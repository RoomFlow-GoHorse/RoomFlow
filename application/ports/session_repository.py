from datetime import datetime
from typing import Protocol

from models.domain.entities.user_session import UserSession


class SessionRepository(Protocol):
    def save(self, session: UserSession) -> None: ...

    def revoke_user(self, user_id: str, at: datetime, institution_id: str | None = None) -> None: ...

    def find_by_digest(self, token_digest: str) -> UserSession | None: ...
