from threading import RLock
from collections.abc import Iterable

from models.domain.exceptions import DuplicateResource
from models.domain.entities.user_account import UserAccount


class InMemoryUserRepository:
    """Temporary process-local user store for development and tests."""

    def __init__(self, accounts: Iterable[UserAccount] = ()) -> None:
        self._lock = RLock()
        self._by_email: dict[str, UserAccount] = {}
        self._by_id: dict[str, UserAccount] = {}
        for account in accounts:
            self._by_email[account.user.email.strip().lower()] = account
            self._by_id[account.user.id] = account

    def find_by_email(self, email: str) -> UserAccount | None:
        with self._lock:
            return self._by_email.get(email.strip().lower())

    def find_by_id(self, user_id: str) -> UserAccount | None:
        with self._lock:
            return self._by_id.get(user_id)

    def list_by_institution(self, institution_id: str) -> tuple[UserAccount, ...]:
        with self._lock:
            return tuple(
                account for account in self._by_id.values()
                if account.user.institution_id == institution_id
            )

    def add(self, account: UserAccount) -> None:
        email = account.user.email.strip().lower()
        with self._lock:
            if email in self._by_email:
                raise DuplicateResource("Já existe uma conta com este e-mail.")
            if account.user.id in self._by_id:
                raise DuplicateResource("O identificador da conta já está em uso.")
            self._by_email[email] = account
            self._by_id[account.user.id] = account

    def save(self, account: UserAccount) -> None:
        with self._lock:
            current = self._by_id.get(account.user.id)
            if current is None:
                raise KeyError(account.user.id)
            normalized_email = account.user.email.strip().lower()
            existing = self._by_email.get(normalized_email)
            if existing is not None and existing.user.id != account.user.id:
                raise DuplicateResource("Já existe uma conta com este e-mail.")
            self._by_email.pop(current.user.email.strip().lower(), None)
            self._by_email[normalized_email] = account
            self._by_id[account.user.id] = account
