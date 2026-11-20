from threading import RLock

from models.domain.entities.user_session import UserSession


class InMemorySessionRepository:
    """Temporary process-local session store; records contain token digests only."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: dict[str, UserSession] = {}

    def save(self, session: UserSession) -> None:
        with self._lock:
            self._sessions[session.token_digest] = session

    def find_by_digest(self, token_digest: str) -> UserSession | None:
        with self._lock:
            return self._sessions.get(token_digest)
