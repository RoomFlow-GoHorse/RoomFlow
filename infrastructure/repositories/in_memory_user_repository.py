from threading import RLock
from collections.abc import Iterable

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
