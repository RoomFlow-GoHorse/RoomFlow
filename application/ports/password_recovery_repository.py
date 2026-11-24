from datetime import datetime
from typing import Protocol


class PasswordRecoveryRepository(Protocol):
    def issue(self, digest: str, user_id: str, expires_at: datetime, now: datetime) -> None: ...

    def consume(self, digest: str, now: datetime) -> str | None: ...
