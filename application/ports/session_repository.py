from typing import Protocol

from models.domain.entities.user_session import UserSession


class SessionRepository(Protocol):
    def save(self, session: UserSession) -> None: ...

    def find_by_digest(self, token_digest: str) -> UserSession | None: ...
