import secrets
from dataclasses import dataclass, replace

from application.ports.institution_repository import InstitutionRepository
from application.ports.password_hasher import PasswordHasher
from application.ports.user_repository import UserRepository
from models.domain.entities.institution import Institution
from models.domain.entities.permission import Permission
from models.domain.entities.profile import Profile
from models.domain.entities.user import User, UserStatus
from models.domain.entities.user_account import UserAccount
from models.domain.exceptions import DuplicateResource, ResourceNotFound
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


class InstitutionManagementService:
    """Registration and own-institution settings use cases."""

    def __init__(
        self,
        institutions: InstitutionRepository,
        users: UserRepository,
        password_hasher: PasswordHasher,
        permission_policy: PermissionPolicy | None = None,
    ) -> None:
        self._institutions = institutions
        self._users = users
        self._password_hasher = password_hasher
        self._permissions = permission_policy or PermissionPolicy()

    def register(self, data: InstitutionRegistration) -> tuple[Institution, User]:
        cnpj = "".join(character for character in data.cnpj if character.isdigit())
        if len(cnpj) != 14:
            raise ValueError("O CNPJ deve conter 14 dígitos.")
        if self._institutions.find_by_cnpj(cnpj):
            raise DuplicateResource("Já existe uma instituição com este CNPJ.")
        email = data.responsible_email.strip().lower()
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
            email=data.email.strip().lower(),
        )
        owner = User(
            id=f"u-{secrets.token_urlsafe(12)}",
            name=data.responsible_name.strip(),
            email=email,
            profile=Profile.ADMIN,
            institution_id=institution.id,
            status=UserStatus.ACTIVE,
        )
        account = UserAccount(owner, self._password_hasher.hash_password(data.password))

        # Compensating rollback keeps both in-memory writes together if user creation fails.
        self._institutions.add(institution)
        try:
            self._users.add(account)
        except Exception:
            self._institutions.remove(institution.id)
            raise
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

    def update_own(self, actor: User, data: InstitutionUpdate) -> Institution:
        current = self.get_own(actor)
        updated = replace(
            current,
            name=data.name.strip(),
            institution_type=(data.institution_type if data.institution_type is not None else current.institution_type),
            city=data.city if data.city is not None else current.city,
            state=data.state.upper() if data.state is not None else current.state,
            phone=data.phone if data.phone is not None else current.phone,
            email=(data.email.strip().lower() if data.email is not None else current.email),
        )
        self._institutions.save(updated)
        return updated
