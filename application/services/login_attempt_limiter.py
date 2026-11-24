from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import RLock


class LoginAttemptLimiter:
    """In-memory sliding window used to slow repeated local login failures."""

    def __init__(self, max_attempts: int = 5, window: timedelta = timedelta(minutes=1)) -> None:
        self._max_attempts = max_attempts
        self._window = window
        self._failures: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = RLock()

    def register_attempt(self, key: str, now: datetime) -> bool:
        with self._lock:
            failures = self._failures[key]
            self._discard_expired(failures, now)
            if len(failures) >= self._max_attempts:
                return False
            failures.append(now)
            return True

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def _discard_expired(self, failures: deque[datetime], now: datetime) -> None:
        cutoff = now - self._window
        while failures and failures[0] <= cutoff:
            failures.popleft()
