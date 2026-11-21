import secrets
import re
from dataclasses import replace
from datetime import datetime, timezone

from application.ports.clock import Clock
from application.services.admin_audit_service import AdminAuditService, audited_mutation
from application.ports.institution_repository import InstitutionRepository
from application.ports.password_hasher import PasswordHasher
from application.ports.session_repository import SessionRepository
from application.ports.user_repository import UserRepository
from models.domain.entities.institution import Institution
from models.domain.entities.admin_audit_event import AdminAuditAction
from models.domain.entities.permission import Permission
from models.domain.entities.profile import Profile
from models.domain.entities.user import User, UserStatus
from models.domain.entities.user_account import UserAccount
from models.domain.exceptions import DuplicateResource, InstitutionAccessDenied, PermissionDenied, ResourceNotFound
from models.domain.identity_normalization import normalize_email
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
        audit: AdminAuditService | None = None,
        sessions: SessionRepository | None = None,
    ) -> None:
        self._users = users
        self._institutions = institutions
        self._password_hasher = password_hasher
        self._permissions = permission_policy or PermissionPolicy()
        self._clock = clock
        self._audit = audit
        self._sessions = sessions

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
        return self._account_in_scope(actor, user_id).user

    @audited_mutation
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
        normalized_email = normalize_email(email)
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
        user = self._users.add(UserAccount(user, self._password_hasher.hash_password(password))).user
        self._record(actor, AdminAuditAction.USER_CREATED, "user", user.id)
        return user

    @audited_mutation
    def update_user(self, actor: User, user_id: str, name: str, email: str) -> User:
        account = self._account_in_scope(actor, user_id)
        if actor.id != user_id and self._users.has_other_memberships(user_id, actor.institution_id or ""):
            raise PermissionDenied("Somente o titular pode editar os dados de uma conta com vários vínculos.")
        return self._update_identity(actor, account, name, email)

    @audited_mutation
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
        if account.user.profile is not updated.profile:
            self._record(actor, AdminAuditAction.USER_PROFILE_CHANGED, "user", updated.id)
        return updated

    @audited_mutation
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
        if account.user.is_active and not updated.is_active and self._sessions is not None:
            now = self._clock.now() if self._clock else datetime.now(timezone.utc)
            self._sessions.revoke_user(updated.id, now, updated.institution_id)
        if account.user.status is not updated.status:
            action = AdminAuditAction.USER_ACTIVATED if updated.is_active else AdminAuditAction.USER_DEACTIVATED
            self._record(actor, action, "user", updated.id)
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

    @audited_mutation
    def update_own_profile(self, actor: User, name: str, email: str) -> User:
        self._permissions.authorize_own_account(actor, actor.id)
        account = self._users.find_by_id(actor.id, actor.institution_id)
        if account is None:
            raise ResourceNotFound("Usuário não encontrado.")
        return self._update_identity(actor, account, name, email)

    def _update_identity(self, actor: User, account: UserAccount, name: str, email: str) -> User:
        name = name.strip()
        normalized_email = normalize_email(email)
        if not name or len(name) > 150 or len(normalized_email) > 255:
            raise ValueError("Informe nome e e-mail dentro dos limites permitidos.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
            raise ValueError("Informe um e-mail válido.")
        existing = self._users.find_by_email(normalized_email)
        if existing is not None and existing.user.id != account.user.id:
            raise DuplicateResource("Já existe uma conta com este e-mail.")
        updated = replace(
            account.user, name=name.strip(), email=normalized_email
        )
        self._users.save(replace(account, user=updated))
        if actor.institution_id and actor.profile is Profile.ADMIN and updated != account.user:
            self._record(actor, AdminAuditAction.USER_ACCOUNT_UPDATED, "user", updated.id)
        return updated

    def _record(self, actor: User, action: AdminAuditAction, resource_type: str, resource_id: str) -> None:
        if self._audit is not None:
            self._audit.record(actor, action, resource_type, resource_id)

    def _account_in_scope(self, actor: User, user_id: str) -> UserAccount:
        self._permissions.authorize_listing(actor, Permission.MANAGE_USERS)
        account = self._users.find_by_id(user_id, actor.institution_id)
        if account is None:
            if self._users.find_by_id(user_id) is not None:
                raise InstitutionAccessDenied("O recurso pertence a outra instituição.")
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
