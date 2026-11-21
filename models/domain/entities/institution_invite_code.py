from dataclasses import dataclass, field, replace
from datetime import datetime
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class InstitutionInviteCode:
    institution_id: str
    digest: str
    created_at: datetime
    revoked_at: datetime | None = None
    id: str = field(default_factory=lambda: f"invite-{uuid4().hex}")

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def revoke(self, instant: datetime) -> "InstitutionInviteCode":
        if self.revoked_at is not None:
            return self
        return replace(self, revoked_at=instant)
