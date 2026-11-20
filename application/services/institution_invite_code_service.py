import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from application.ports.institution_invite_code_repository import InstitutionInviteCodeRepository
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
    ) -> None:
        self._repository = repository
        self._policy = policy or PermissionPolicy()

    def status_for(
        self, actor: User, requested_institution_id: str | None = None
    ) -> InvitationCodeStatus:
        institution_id = self._institution_scope(actor, requested_institution_id)
        code = self._repository.find_active(institution_id)
        return InvitationCodeStatus(bool(code), code.created_at if code else None)

    def issue_or_replace(
        self, actor: User, requested_institution_id: str | None = None
    ) -> tuple[str, InvitationCodeStatus]:
        institution_id = self._institution_scope(actor, requested_institution_id)
        for _ in range(5):
            raw_code = secrets.token_urlsafe(24)
            entity = InstitutionInviteCode(
                institution_id=institution_id,
                digest=self._digest(raw_code),
                created_at=datetime.now(timezone.utc),
            )
            try:
                self._repository.replace(entity)
                return raw_code, InvitationCodeStatus(True, entity.created_at)
            except ValueError:
                continue
        raise RuntimeError("Não foi possível gerar um código institucional único.")

    def resolve_active_code(self, raw_code: str) -> str | None:
        if not raw_code or len(raw_code) > 200:
            return None
        record = self._repository.find_active_by_digest(self._digest(raw_code))
        return record.institution_id if record else None

    def _institution_scope(
        self, actor: User, requested_institution_id: str | None = None
    ) -> str:
        return self._policy.authorize_listing(
            actor, Permission.EDIT_INSTITUTION_SETTINGS, requested_institution_id
        )

    @staticmethod
    def _digest(raw_code: str) -> str:
        return hashlib.sha256(raw_code.encode("utf-8")).hexdigest()
