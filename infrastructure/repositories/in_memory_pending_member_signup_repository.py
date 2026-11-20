from datetime import datetime
from threading import RLock

from models.domain.entities.pending_member_signup import PendingMemberSignup


class InMemoryPendingMemberSignupRepository:
    """Temporary process-local store; keeps only verification-token digests."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._items: dict[str, PendingMemberSignup] = {}

    def save(self, signup: PendingMemberSignup) -> None:
        with self._lock:
            self._items[signup.token_digest] = signup

    def find_by_digest(self, digest: str) -> PendingMemberSignup | None:
        with self._lock:
            return self._items.get(digest)

    def delete(self, digest: str) -> None:
        with self._lock:
            self._items.pop(digest, None)

    def delete_expired(self, now: datetime) -> None:
        with self._lock:
            self._items = {
                digest: item for digest, item in self._items.items()
                if item.expires_at > now
            }
