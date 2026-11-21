import secrets
import re
from dataclasses import dataclass
from threading import RLock
from typing import Any

from application.ports.authorized_enrollment_repository import AuthorizedEnrollmentRepository
from application.services.admin_audit_service import AdminAuditService, audited_mutation
from application.ports.institution_repository import InstitutionRepository
from application.ports.enrollment_spreadsheet_parser import EnrollmentSpreadsheetParser
from application.services.institution_invite_code_service import InstitutionInviteCodeService
from application.services.login_attempt_limiter import LoginAttemptLimiter
from models.domain.entities.authorized_enrollment import AuthorizedEnrollment, EnrollmentStatus
from models.domain.entities.admin_audit_event import AdminAuditAction
from models.domain.entities.permission import Permission
from models.domain.entities.user import User
from models.domain.exceptions import DuplicateResource, ResourceNotFound
from models.domain.policies.permission_policy import PermissionPolicy


@dataclass(frozen=True, slots=True)
class ImportRowResult:
    row_number: int
    registration_number: str | None
    name: str | None
    email: str | None
    status: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class EnrollmentImportPreview:
    preview_id: str
    valid: tuple[ImportRowResult, ...]
    duplicates: tuple[ImportRowResult, ...]
    invalid: tuple[ImportRowResult, ...]


@dataclass(frozen=True, slots=True)
class MemberInstitutionPreview:
    institution_id: str
    institution_name: str


class EnrollmentManagementService:
    """Institution-scoped enrollment operations and member eligibility preview."""

    def __init__(
        self,
        enrollments: AuthorizedEnrollmentRepository,
        institutions: InstitutionRepository,
        invite_codes: InstitutionInviteCodeService,
        spreadsheet_parser: EnrollmentSpreadsheetParser,
        policy: PermissionPolicy | None = None,
        attempt_limiter: LoginAttemptLimiter | None = None,
        audit: AdminAuditService | None = None,
    ) -> None:
        self._enrollments = enrollments
        self._institutions = institutions
        self._invite_codes = invite_codes
        self._spreadsheet_parser = spreadsheet_parser
        self._policy = policy or PermissionPolicy()
        self._attempt_limiter = attempt_limiter
        self._audit = audit
        self._previews: dict[str, tuple[str, tuple[AuthorizedEnrollment, ...]]] = {}
        self._preview_lock = RLock()

    @audited_mutation
    def add_manual(
        self,
        actor: User,
        registration_number: str,
        name: str | None = None,
        email: str | None = None,
    ) -> AuthorizedEnrollment:
        institution_id = self._admin_scope(actor)
        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
            raise ValueError("Informe um e-mail válido para a matrícula.")
        enrollment = AuthorizedEnrollment(
            id=f"enr-{secrets.token_urlsafe(12)}",
            institution_id=institution_id,
            registration_number=registration_number,
            name=name,
            email=email,
        )
        self._enrollments.add(enrollment)
        self._record(actor, AdminAuditAction.ENROLLMENT_CREATED, "authorized_enrollment", enrollment.id)
        return enrollment

    def list_enrollments(
        self,
        actor: User,
        query: str = "",
        status: EnrollmentStatus | None = None,
        requested_institution_id: str | None = None,
    ) -> list[AuthorizedEnrollment]:
        institution_id = self._policy.authorize_listing(
            actor, Permission.MANAGE_USERS, requested_institution_id
        )
        normalized_query = query.strip().casefold()
        return [
            item
            for item in self._enrollments.list_for_institution(institution_id)
            if (status is None or item.status is status)
            and (
                not normalized_query
                or normalized_query in item.registration_number.casefold()
                or normalized_query in (item.name or "").casefold()
                or normalized_query in (item.email or "").casefold()
            )
        ]

    @audited_mutation
    def deactivate(self, actor: User, enrollment_id: str) -> AuthorizedEnrollment:
        institution_id = self._admin_scope(actor)
        enrollment = self._enrollments.find_by_id(institution_id, enrollment_id)
        if enrollment is None:
            raise ResourceNotFound("Matrícula não encontrada.")
        updated = enrollment.deactivate()
        self._enrollments.save(updated)
        self._record(actor, AdminAuditAction.ENROLLMENT_DEACTIVATED, "authorized_enrollment", updated.id)
        return updated

    def preview_import(self, actor: User, content: bytes) -> EnrollmentImportPreview:
        institution_id = self._admin_scope(actor)
        records = self._spreadsheet_parser.parse(content)
        valid: list[ImportRowResult] = []
        duplicates: list[ImportRowResult] = []
        invalid: list[ImportRowResult] = []
        seen: set[str] = set()
        new_enrollments: list[AuthorizedEnrollment] = []

        for index, record in enumerate(records, start=2):
            registration_number = self._optional_text(record.get("registration_number"))
            name = self._optional_text(record.get("name"))
            email = self._optional_text(record.get("email"))
            if not registration_number:
                invalid.append(ImportRowResult(index, None, name, email, "inválido", "Matrícula ausente."))
                continue
            if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                invalid.append(ImportRowResult(index, registration_number, name, email, "inválido", "E-mail inválido."))
                continue

            candidate = AuthorizedEnrollment(
                id=f"enr-{secrets.token_urlsafe(12)}",
                institution_id=institution_id,
                registration_number=registration_number,
                name=name,
                email=email,
            )
            normalized = candidate.normalized_registration_number
            if normalized in seen or self._enrollments.find(institution_id, registration_number):
                duplicates.append(ImportRowResult(index, registration_number, name, email, "duplicado", "Matrícula já cadastrada ou repetida na planilha."))
                continue
            seen.add(normalized)
            new_enrollments.append(candidate)
            valid.append(ImportRowResult(index, registration_number, name, email, "válido"))

        preview_id = secrets.token_urlsafe(24)
        with self._preview_lock:
            self._previews[preview_id] = (institution_id, tuple(new_enrollments))
        return EnrollmentImportPreview(preview_id, tuple(valid), tuple(duplicates), tuple(invalid))

    @audited_mutation
    def confirm_import(self, actor: User, preview_id: str) -> int:
        institution_id = self._admin_scope(actor)
        with self._preview_lock:
            preview = self._previews.get(preview_id)
            if preview is None or preview[0] != institution_id:
                raise ResourceNotFound("Prévia de importação não encontrada.")
            enrollments = preview[1]
            self._enrollments.add_many(enrollments)
            for enrollment in enrollments:
                self._record(actor, AdminAuditAction.ENROLLMENT_IMPORTED, "authorized_enrollment", enrollment.id)
            del self._previews[preview_id]
        return len(enrollments)

    def preview_member_institution(
        self,
        raw_code: str,
        registration_number: str,
        name: str,
        email: str,
        attempt_key: str,
    ) -> MemberInstitutionPreview:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        if self._attempt_limiter and not self._attempt_limiter.register_attempt(attempt_key, now):
            raise TooManyEnrollmentAttempts

        institution_id = self._invite_codes.resolve_active_code(raw_code)
        enrollment = (
            self._enrollments.find(institution_id, registration_number)
            if institution_id is not None
            else None
        )
        valid = bool(enrollment and enrollment.is_available)
        if valid and enrollment:
            valid = self._matches_if_present(enrollment.name, name)
            valid = valid and self._matches_if_present(enrollment.email, email)
        if not valid or institution_id is None:
            raise MemberIdentityNotConfirmed
        institution = self._institutions.find_by_id(institution_id)
        if institution is None:
            raise MemberIdentityNotConfirmed
        if self._attempt_limiter:
            self._attempt_limiter.record_success(attempt_key)
        return MemberInstitutionPreview(institution.id, institution.name)

    def _admin_scope(self, actor: User) -> str:
        return self._policy.authorize_listing(actor, Permission.MANAGE_USERS)

    def _record(self, actor: User, action: AdminAuditAction, resource_type: str, resource_id: str) -> None:
        if self._audit is not None:
            self._audit.record(actor, action, resource_type, resource_id)

    @staticmethod
    def _matches_if_present(expected: str | None, supplied: str) -> bool:
        if expected is None:
            return True
        return " ".join(expected.split()).casefold() == " ".join(supplied.split()).casefold()

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class MemberIdentityNotConfirmed(Exception):
    pass


class TooManyEnrollmentAttempts(Exception):
    pass
