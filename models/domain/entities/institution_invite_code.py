from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class InstitutionInviteCode:
    institution_id: str
    digest: str
    created_at: datetime
    revoked_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def revoke(self, instant: datetime) -> "InstitutionInviteCode":
        if self.revoked_at is not None:
            return self
        from dataclasses import replace
        return replace(self, revoked_at=instant)
