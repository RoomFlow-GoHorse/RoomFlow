import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from application.ports.institution_invite_code_repository import InstitutionInviteCodeRepository
from application.services.admin_audit_service import AdminAuditService, audited_mutation
from models.domain.entities.admin_audit_event import AdminAuditAction
from models.domain.entities.institution_invite_code import InstitutionInviteCode
from models.domain.entities.permission import Permission
from models.domain.entities.user import User
from models.domain.policies.permission_policy import PermissionPolicy


@dataclass(frozen=True, slots=True)
class InvitationCodeStatus:
    active: bool
    created_at: datetime | None


class InstitutionInviteCodeService:
    """Issues one-time revealable invitation secrets for an admin's institution."""

    def __init__(
        self,
        repository: InstitutionInviteCodeRepository,
        policy: PermissionPolicy | None = None,
        audit: AdminAuditService | None = None,
    ) -> None:
        self._repository = repository
        self._policy = policy or PermissionPolicy()
        self._audit = audit

    def status_for(
        self, actor: User, requested_institution_id: str | None = None
    ) -> InvitationCodeStatus:
        institution_id = self._institution_scope(actor, requested_institution_id)
        code = self._repository.find_active(institution_id)
        return InvitationCodeStatus(bool(code), code.created_at if code else None)

    @audited_mutation
    def issue_or_replace(
        self, actor: User, requested_institution_id: str | None = None
    ) -> tuple[str, InvitationCodeStatus]:
        institution_id = self._institution_scope(actor, requested_institution_id)
        replacing = self._repository.find_active(institution_id) is not None
        for _ in range(5):
            raw_code = secrets.token_urlsafe(24)
            entity = InstitutionInviteCode(
                institution_id=institution_id,
                digest=self.digest_code(raw_code),
                created_at=datetime.now(timezone.utc),
            )
            try:
                self._repository.replace(entity)
            except ValueError:
                continue
            if self._audit is not None:
                action = AdminAuditAction.INVITATION_CODE_REPLACED if replacing else AdminAuditAction.INVITATION_CODE_GENERATED
                self._audit.record(actor, action, "institution_invitation_code", entity.id)
            return raw_code, InvitationCodeStatus(True, entity.created_at)
        raise RuntimeError("Não foi possível gerar um código institucional único.")

    @audited_mutation
    def revoke(
        self, actor: User, requested_institution_id: str | None = None
    ) -> InvitationCodeStatus:
        institution_id = self._institution_scope(actor, requested_institution_id)
        revoked = self._repository.revoke(institution_id, datetime.now(timezone.utc))
        if revoked is not None and self._audit is not None:
            self._audit.record(
                actor,
                AdminAuditAction.INVITATION_CODE_REVOKED,
                "institution_invitation_code",
                revoked.id,
            )
        return InvitationCodeStatus(False, revoked.created_at if revoked else None)

    def resolve_active_code(self, raw_code: str) -> str | None:
        if not raw_code or len(raw_code) > 200:
            return None
        return self.resolve_active_digest(self.digest_code(raw_code))

    def resolve_active_digest(self, digest: str) -> str | None:
        record = self._repository.find_active_by_digest(digest)
        return record.institution_id if record else None

    def _institution_scope(
        self, actor: User, requested_institution_id: str | None = None
    ) -> str:
        return self._policy.authorize_listing(
            actor, Permission.EDIT_INSTITUTION_SETTINGS, requested_institution_id
        )

    @staticmethod
    def digest_code(raw_code: str) -> str:
        return hashlib.sha256(raw_code.encode("utf-8")).hexdigest()
