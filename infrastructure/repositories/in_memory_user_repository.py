from threading import RLock
from collections.abc import Iterable

from infrastructure.in_memory_admin_transaction import InMemoryAdminTransaction
from models.domain.exceptions import DuplicateResource, LastActiveAdministrator, ResourceNotFound
from models.domain.entities.user_account import UserAccount
from models.domain.entities.profile import Profile
from models.domain.entities.user import UserStatus
from models.domain.identity_normalization import normalize_email


class InMemoryUserRepository:
    """Temporary process-local user store for development and tests."""

    def __init__(self, accounts: Iterable[UserAccount] = (), *, transaction: InMemoryAdminTransaction | None = None) -> None:
        self._lock = transaction.lock if transaction is not None else RLock()
        self._by_email: dict[str, UserAccount] = {}
        self._by_id: dict[str, UserAccount] = {}
        if transaction is not None:
            transaction.register(self._by_email, self._by_id)
        for account in accounts:
            self._by_email[normalize_email(account.user.email)] = account
            self._by_id[account.user.id] = account

    def find_by_email(self, email: str) -> UserAccount | None:
        with self._lock:
            return self._by_email.get(normalize_email(email))

    def list_login_accounts(self, email: str) -> tuple[UserAccount, ...]:
        account = self.find_by_email(email)
        return (account,) if account else ()

    def find_by_id(self, user_id: str, institution_id: str | None = None) -> UserAccount | None:
        with self._lock:
            account = self._by_id.get(user_id)
            if account and institution_id is not None and account.user.institution_id != institution_id:
                return None
            return account

    def list_by_institution(self, institution_id: str) -> tuple[UserAccount, ...]:
        with self._lock:
            return tuple(
                account for account in self._by_id.values()
                if account.user.institution_id == institution_id
            )

    def has_other_memberships(self, user_id: str, institution_id: str) -> bool:
        with self._lock:
            account = self._by_id.get(user_id)
            return bool(account and account.user.institution_id != institution_id)

    def add(self, account: UserAccount) -> UserAccount:
        email = normalize_email(account.user.email)
        with self._lock:
            if email in self._by_email:
                raise DuplicateResource("Já existe uma conta com este e-mail.")
            if account.user.id in self._by_id:
                raise DuplicateResource("O identificador da conta já está em uso.")
            self._by_email[email] = account
            self._by_id[account.user.id] = account
            return account

    def save(self, account: UserAccount) -> None:
        with self._lock:
            self._save_unlocked(account)

    def save_preserving_active_admin(
        self, account: UserAccount, institution_id: str
    ) -> None:
        """Atomically apply an administrator change while preserving an active admin."""
        with self._lock:
            current = self._by_id.get(account.user.id)
            if (
                current is None
                or current.user.institution_id != institution_id
                or account.user.institution_id != institution_id
            ):
                raise ResourceNotFound("Usu\u00e1rio n\u00e3o encontrado.")

            active_admins_after_change = sum(
                1
                for user_id, stored in self._by_id.items()
                if user_id != account.user.id
                and stored.user.institution_id == institution_id
                and stored.user.profile is Profile.ADMIN
                and stored.user.status is UserStatus.ACTIVE
            )
            if account.user.profile is Profile.ADMIN and account.user.status is UserStatus.ACTIVE:
                active_admins_after_change += 1
            if active_admins_after_change < 1:
                raise LastActiveAdministrator(
                    "A institui\u00e7\u00e3o precisa manter pelo menos um administrador ativo."
                )
            self._save_unlocked(account)

    def _save_unlocked(self, account: UserAccount) -> None:
        current = self._by_id.get(account.user.id)
        if current is None:
            raise ResourceNotFound("Usu\u00e1rio n\u00e3o encontrado.")
        normalized_email = normalize_email(account.user.email)
        existing = self._by_email.get(normalized_email)
        if existing is not None and existing.user.id != account.user.id:
            raise DuplicateResource("J\u00e1 existe uma conta com este e-mail.")
        self._by_email.pop(normalize_email(current.user.email), None)
        self._by_email[normalized_email] = account
        self._by_id[account.user.id] = account
