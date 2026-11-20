import secrets
from dataclasses import replace

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


class UserManagementService:
    """Use cases for institution-scoped user administration."""

    def __init__(
        self,
        users: UserRepository,
        institutions: InstitutionRepository,
        password_hasher: PasswordHasher,
        permission_policy: PermissionPolicy | None = None,
    ) -> None:
        self._users = users
        self._institutions = institutions
        self._password_hasher = password_hasher
        self._permissions = permission_policy or PermissionPolicy()

    def list_users(
        self,
        actor: User,
        query: str = "",
        requested_institution_id: str | None = None,
    ) -> list[User]:
        institution_id = self._permissions.authorize_listing(
            actor, Permission.MANAGE_USERS, requested_institution_id
        )
        search = query.strip().casefold()
        accounts = self._users.list_by_institution(institution_id)
        return [
            account.user
            for account in accounts
            if not search
            or search in account.user.name.casefold()
            or search in account.user.email.casefold()
        ]

    def get_user(self, actor: User, user_id: str) -> User:
        self._permissions.authorize_listing(actor, Permission.MANAGE_USERS)
        account = self._users.find_by_id(user_id)
        if account is None:
            raise ResourceNotFound("Usuário não encontrado.")
        institution = self._institution_for_user(account.user)
        self._permissions.authorize_resource(
            actor, Permission.MANAGE_USERS, institution
        )
        return account.user

    def create_user(
        self,
        actor: User,
        name: str,
        email: str,
        password: str,
        profile: Profile = Profile.REQUESTER,
    ) -> User:
        institution_id = self._permissions.authorize_listing(
            actor, Permission.MANAGE_USERS
        )
        normalized_email = email.strip().lower()
        if self._users.find_by_email(normalized_email):
            raise DuplicateResource("Já existe uma conta com este e-mail.")
        user = User(
            id=f"u-{secrets.token_urlsafe(12)}",
            name=name.strip(),
            email=normalized_email,
            profile=Profile(profile),
            institution_id=institution_id,
            status=UserStatus.ACTIVE,
        )
        self._users.add(UserAccount(user, self._password_hasher.hash_password(password)))
        return user

    def update_profile(self, actor: User, user_id: str, profile: Profile) -> User:
        account = self._account_in_scope(actor, user_id)
        updated = replace(account.user, profile=Profile(profile))
        saved = replace(account, user=updated)
        self._users.save(saved)
        return updated

    def set_status(self, actor: User, user_id: str, status: UserStatus) -> User:
        account = self._account_in_scope(actor, user_id)
        updated = replace(account.user, status=UserStatus(status))
        self._users.save(replace(account, user=updated))
        return updated

    def update_own_profile(self, actor: User, name: str, email: str) -> User:
        self._permissions.authorize_own_account(actor, actor.id)
        account = self._users.find_by_id(actor.id)
        if account is None:
            raise ResourceNotFound("Usuário não encontrado.")
        normalized_email = email.strip().lower()
        existing = self._users.find_by_email(normalized_email)
        if existing is not None and existing.user.id != actor.id:
            raise DuplicateResource("Já existe uma conta com este e-mail.")
        updated = replace(
            account.user, name=name.strip(), email=normalized_email
        )
        self._users.save(replace(account, user=updated))
        return updated

    def _account_in_scope(self, actor: User, user_id: str) -> UserAccount:
        self._permissions.authorize_listing(actor, Permission.MANAGE_USERS)
        account = self._users.find_by_id(user_id)
        if account is None:
            raise ResourceNotFound("Usuário não encontrado.")
        self._permissions.authorize_resource(
            actor,
            Permission.MANAGE_USERS,
            self._institution_for_user(account.user),
        )
        return account

    def _institution_for_user(self, user: User) -> Institution:
        institution_id = user.institution_id
        institution = (
            self._institutions.find_by_id(institution_id)
            if institution_id is not None
            else None
        )
        if institution is None:
            raise ResourceNotFound("Instituição do usuário não encontrada.")
        return institution
