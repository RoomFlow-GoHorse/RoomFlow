import secrets
import re
from dataclasses import replace

from application.ports.clock import Clock
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
        clock: Clock | None = None,
    ) -> None:
        self._users = users
        self._institutions = institutions
        self._password_hasher = password_hasher
        self._permissions = permission_policy or PermissionPolicy()
        self._clock = clock

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
        clean_name = name.strip()
        normalized_email = email.strip().lower()
        if not clean_name:
            raise ValueError("Informe o nome do usuário.")
        if len(clean_name) > 150 or len(normalized_email) > 255:
            raise ValueError("Nome ou e-mail excede o tamanho permitido.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
            raise ValueError("Informe um e-mail válido.")
        if len(password) < 8:
            raise ValueError("A senha deve possuir pelo menos 8 caracteres.")
        if len(password) > 1024:
            raise ValueError("A senha excede o tamanho permitido.")
        if self._users.find_by_email(normalized_email):
            raise DuplicateResource("Já existe uma conta com este e-mail.")
        user = User(
            id=f"u-{secrets.token_urlsafe(12)}",
            name=clean_name,
            email=normalized_email,
            profile=Profile(profile),
            institution_id=institution_id,
            status=UserStatus.ACTIVE,
            created_at=self._clock.now() if self._clock is not None else None,
        )
        self._users.add(UserAccount(user, self._password_hasher.hash_password(password)))
        return user

    def update_profile(self, actor: User, user_id: str, profile: Profile) -> User:
        account = self._account_in_scope(actor, user_id)
        updated = replace(account.user, profile=Profile(profile))
        saved = replace(account, user=updated)
        if self._is_removing_active_admin(account.user, updated):
            self._users.save_preserving_active_admin(
                saved, account.user.institution_id or ""
            )
        else:
            self._users.save(saved)
        return updated

    def set_status(self, actor: User, user_id: str, status: UserStatus) -> User:
        account = self._account_in_scope(actor, user_id)
        updated = replace(account.user, status=UserStatus(status))
        saved = replace(account, user=updated)
        if self._is_removing_active_admin(account.user, updated):
            self._users.save_preserving_active_admin(
                saved, account.user.institution_id or ""
            )
        else:
            self._users.save(saved)
        return updated

    @staticmethod
    def _is_removing_active_admin(current: User, updated: User) -> bool:
        return (
            current.profile is Profile.ADMIN
            and current.status is UserStatus.ACTIVE
            and (
                updated.profile is not Profile.ADMIN
                or updated.status is not UserStatus.ACTIVE
            )
        )

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
