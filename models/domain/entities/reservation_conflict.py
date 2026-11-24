from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from models.domain.entities.reservation import EDITABLE, ReservationDetails, ReservationStatus


class ConflictStatus(StrEnum):
    OPEN = "nao_resolvido"
    IN_REVIEW = "em_analise"
    RESOLVED = "resolvido"


class ConflictAction(StrEnum):
    KEEP_A = "manteve_a"
    KEEP_B = "manteve_b"
    MOVE = "alterou"


@dataclass(frozen=True, slots=True)
class ReservationConflict:
    id: str
    institution_id: str
    reservation_a_id: str
    reservation_b_id: str
    status: ConflictStatus
    severity: str
    reason: str
    created_at: datetime
    decision: str | None
    resolved_at: datetime | None
    resolved_by: str | None
    resolver_name: str | None = None


@dataclass(frozen=True, slots=True)
class ConflictDetails:
    conflict: ReservationConflict
    reservation_a: ReservationDetails
    reservation_b: ReservationDetails

    def is_active(self, now: datetime) -> bool:
        a, b = self.reservation_a.reservation, self.reservation_b.reservation
        return (
            self.conflict.status is not ConflictStatus.RESOLVED
            and a.status in EDITABLE and b.status in EDITABLE
            and a.request.space_id == b.request.space_id
            and min(a.request.period.end, b.request.period.end) > now
            and a.request.period.start < b.request.period.end
            and b.request.period.start < a.request.period.end
        )

    def actions(self, now: datetime) -> tuple[ConflictAction, ...]:
        if not self.is_active(now):
            return ()
        a, b = self.reservation_a.reservation, self.reservation_b.reservation
        actions = []
        if b.status is not ReservationStatus.APPROVED and (
            a.status is ReservationStatus.APPROVED or a.request.period.start > now
        ):
            actions.append(ConflictAction.KEEP_A)
        if a.status is not ReservationStatus.APPROVED and (
            b.status is ReservationStatus.APPROVED or b.request.period.start > now
        ):
            actions.append(ConflictAction.KEEP_B)
        if max(a.request.period.start, b.request.period.start) > now:
            actions.append(ConflictAction.MOVE)
        return tuple(actions)
