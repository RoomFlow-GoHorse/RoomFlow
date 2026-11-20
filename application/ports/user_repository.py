from typing import Protocol

from models.domain.entities.user_account import UserAccount


class UserRepository(Protocol):
    def find_by_email(self, email: str) -> UserAccount | None: ...

    def find_by_id(self, user_id: str) -> UserAccount | None: ...
