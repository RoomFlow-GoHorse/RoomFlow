from datetime import datetime
from threading import RLock

from infrastructure.in_memory_admin_transaction import InMemoryAdminTransaction
from models.domain.entities.user_session import UserSession


class InMemorySessionRepository:
    """Temporary process-local session store; records contain token digests only."""

    def __init__(self, *, transaction: InMemoryAdminTransaction | None = None) -> None:
        self._lock = transaction.lock if transaction is not None else RLock()
        self._sessions: dict[str, UserSession] = {}
        if transaction is not None:
            transaction.register(self._sessions)

    def save(self, session: UserSession) -> None:
        with self._lock:
            self._sessions[session.token_digest] = session

    def revoke_user(self, user_id: str, at: datetime) -> None:
        with self._lock:
            for digest, session in self._sessions.items():
                if session.user_id == user_id and session.is_valid_at(at):
                    self._sessions[digest] = session.revoke(at)

    def find_by_digest(self, token_digest: str) -> UserSession | None:
        with self._lock:
            return self._sessions.get(token_digest)
