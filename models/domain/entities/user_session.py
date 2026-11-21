from dataclasses import dataclass, replace
from datetime import datetime


@dataclass(frozen=True, slots=True)
class UserSession:
    token_digest: str
    user_id: str
    expires_at: datetime
    revoked_at: datetime | None = None

    def is_valid_at(self, instant: datetime) -> bool:
        return self.revoked_at is None and instant < self.expires_at

    def revoke(self, instant: datetime) -> "UserSession":
        if self.revoked_at is not None:
            return self
        return replace(self, revoked_at=instant)
