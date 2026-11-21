from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Notification:
    title: str
    message: str
    category: str
    created_at: datetime
    reservation_id: str | None = None
    conflict_id: str | None = None
    id: str = ""
    read_at: datetime | None = None
