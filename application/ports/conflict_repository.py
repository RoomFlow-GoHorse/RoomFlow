from datetime import datetime
from typing import Protocol

from models.domain.entities.reservation_conflict import ConflictStatus, ReservationConflict


class ConflictRepository(Protocol):
    def list(self, institution_id: str, status: ConflictStatus | None = None) -> list[ReservationConflict]: ...

    def find(self, institution_id: str, conflict_id: str) -> ReservationConflict | None: ...

    def synchronize(
        self, institution_id: str, now: datetime, actor_id: str, reservation_id: str | None = None,
    ) -> int: ...

    def resolve(self, conflict: ReservationConflict, decision: str, actor_id: str, now: datetime) -> None: ...
