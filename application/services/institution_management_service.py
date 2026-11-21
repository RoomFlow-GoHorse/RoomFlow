import secrets
import re
from contextlib import nullcontext
from dataclasses import dataclass, replace

from application.ports.clock import Clock
from application.services.admin_audit_service import AdminAuditService, audited_mutation
from application.services.institution_invite_code_service import InstitutionInviteCodeService
from application.ports.institution_repository import InstitutionRepository
from application.ports.password_hasher import PasswordHasher
from application.ports.user_repository import UserRepository
from models.domain.entities.institution import Institution, InstitutionPreferences
from models.domain.entities.admin_audit_event import AdminAuditAction
from models.domain.entities.permission import Permission
from models.domain.entities.profile import Profile
from models.domain.entities.user import User, UserStatus
from models.domain.entities.user_account import UserAccount
from models.domain.exceptions import DuplicateResource, ResourceNotFound
from models.domain.identity_normalization import normalize_cnpj, normalize_email
from models.domain.policies.permission_policy import PermissionPolicy


@dataclass(frozen=True, slots=True)
class InstitutionRegistration:
    name: str
    cnpj: str
    institution_type: str
    city: str
    state: str
    phone: str
    email: str
    responsible_name: str
    responsible_email: str
    password: str


@dataclass(frozen=True, slots=True)
class InstitutionUpdate:
    name: str
    institution_type: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    timezone: str | None = None
    preferences: InstitutionPreferences | None = None


class InstitutionManagementService:
    """Registration and own-institution settings use cases."""

    def __init__(
        self,
        institutions: InstitutionRepository,
        users: UserRepository,
        password_hasher: PasswordHasher,
        permission_policy: PermissionPolicy | None = None,
        clock: Clock | None = None,
        audit: AdminAuditService | None = None,
    ) -> None:
        self._institutions = institutions
        self._users = users
        self._password_hasher = password_hasher
        self._permissions = permission_policy or PermissionPolicy()
        self._clock = clock
        self._audit = audit

    def register(self, data: InstitutionRegistration) -> tuple[Institution, User]:
        with self._audit.atomic() if self._audit is not None else nullcontext():
            return self._register(data)

    def register_with_invitation(
        self, data: InstitutionRegistration, invitation_codes: InstitutionInviteCodeService,
    ) -> tuple[Institution, User, str]:
        with self._audit.atomic() if self._audit is not None else nullcontext():
            institution, owner = self._register(data)
            code, _ = invitation_codes.issue_or_replace(owner)
            return institution, owner, code

    def _register(self, data: InstitutionRegistration) -> tuple[Institution, User]:
        cnpj = normalize_cnpj(data.cnpj)
        if len(cnpj) != 14:
            raise ValueError("O CNPJ deve conter 14 dígitos.")
        if self._institutions.find_by_cnpj(cnpj):
            raise DuplicateResource("Já existe uma instituição com este CNPJ.")
        email = normalize_email(data.responsible_email)
        if len(email) > 255 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Informe um e-mail válido para o administrador.")
        if not 8 <= len(data.password) <= 1024:
            raise ValueError("A senha deve ter entre 8 e 1024 caracteres.")
        if not data.institution_type.strip():
            raise ValueError("Informe o tipo da instituição.")
        if data.email.strip() and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", data.email.strip()):
            raise ValueError("Informe um e-mail institucional válido.")
        if self._users.find_by_email(email):
            raise DuplicateResource("Já existe uma conta com este e-mail.")

        institution = Institution(
            id=f"inst-{secrets.token_urlsafe(12)}",
            name=data.name.strip(),
            cnpj=cnpj,
            institution_type=data.institution_type.strip(),
            city=data.city.strip(),
            state=data.state.strip().upper(),
            phone=data.phone.strip(),
            email=normalize_email(data.email),
        )
        owner = User(
            id=f"u-{secrets.token_urlsafe(12)}",
            name=data.responsible_name.strip(),
            email=email,
            profile=Profile.ADMIN,
            institution_id=institution.id,
            status=UserStatus.ACTIVE,
            created_at=self._clock.now() if self._clock is not None else None,
        )
        account = UserAccount(owner, self._password_hasher.hash_password(data.password))

        # Compensating rollback keeps both in-memory writes together if user creation fails.
        institution = self._institutions.add(institution)
        try:
            owner = self._users.add(replace(account, user=replace(owner, institution_id=institution.id))).user
        except Exception:
            if self._audit is None:
                self._institutions.remove(institution.id)
            raise
        if self._audit is not None:
            self._audit.record(owner, AdminAuditAction.INSTITUTION_CREATED, "institution", institution.id)
            self._audit.record(owner, AdminAuditAction.USER_CREATED, "user", owner.id)
        return institution, owner

    def get_own(self, actor: User) -> Institution:
        self._permissions.authorize_listing(actor, Permission.EDIT_INSTITUTION_SETTINGS)
        institution = self._institutions.find_by_id(actor.institution_id or "")
        if institution is None:
            raise ResourceNotFound("Instituição não encontrada.")
        self._permissions.authorize_resource(
            actor, Permission.EDIT_INSTITUTION_SETTINGS, institution
        )
        return institution

    @audited_mutation
    def update_own(self, actor: User, data: InstitutionUpdate) -> Institution:
        current = self.get_own(actor)
        name = data.name.strip()
        if not name:
            raise ValueError("O nome da instituição é obrigatório.")
        email = normalize_email(data.email) if data.email is not None else current.email
        if data.email is not None and email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Informe um e-mail institucional válido.")
        phone = data.phone.strip() if data.phone is not None else current.phone
        if phone and len(phone) > 30:
            raise ValueError("O telefone deve ter no máximo 30 caracteres.")
        state = data.state.strip().upper() if data.state is not None else current.state
        if state and len(state) != 2:
            raise ValueError("A sigla do estado deve conter 2 caracteres.")
        updated = replace(
            current,
            name=name,
            institution_type=(data.institution_type if data.institution_type is not None else current.institution_type),
            city=data.city.strip() if data.city is not None else current.city,
            state=state,
            phone=phone,
            email=email,
            address=data.address.strip() if data.address is not None else current.address,
            timezone=data.timezone if data.timezone is not None else current.timezone,
            preferences=data.preferences if data.preferences is not None else current.preferences,
        )
        self._institutions.save(updated)
        if self._audit is not None and updated != current:
            self._audit.record(actor, AdminAuditAction.INSTITUTION_SETTINGS_UPDATED, "institution", updated.id)
        return updated
