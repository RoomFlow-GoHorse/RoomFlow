from datetime import datetime
from typing import Protocol

from models.domain.entities.notification import Notification


class NotificationRepository(Protocol):
    def add(self, institution_id: str, item: Notification, recipient_ids: frozenset[str]) -> None: ...

    def inbox(
        self, institution_id: str, user_id: str, *, unread_only: bool,
        category: str | None, limit: int, offset: int,
    ) -> tuple[list[Notification], int]: ...

    def unread_count(self, institution_id: str, user_id: str) -> int: ...

    def mark_read(
        self, institution_id: str, user_id: str, notification_id: str, now: datetime,
    ) -> datetime | None: ...

    def mark_all_read(self, institution_id: str, user_id: str, now: datetime) -> int: ...
