from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum


class ReservationStatus(StrEnum):
    PENDING = "pendente"
    IN_REVIEW = "em_analise"
    APPROVED = "aprovada"
    REJECTED = "rejeitada"
    CONFLICT = "conflito"
    CANCELLED = "cancelada"


REVIEWABLE = frozenset({ReservationStatus.PENDING, ReservationStatus.IN_REVIEW, ReservationStatus.CONFLICT})
EDITABLE = REVIEWABLE | {ReservationStatus.APPROVED}


@dataclass(frozen=True, slots=True)
class ReservationPeriod:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.utcoffset() is None or self.end.utcoffset() is None:
            raise ValueError("Informe início e fim com fuso horário.")
        start = self.start.astimezone(timezone.utc)
        end = self.end.astimezone(timezone.utc)
        if start >= end:
            raise ValueError("O horário de término deve ser posterior ao início.")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)


@dataclass(frozen=True, slots=True)
class ReservationRequest:
    space_id: str
    title: str
    activity_type: str
    period: ReservationPeriod
    participants: int
    justification: str | None = None

    def validated(self) -> "ReservationRequest":
        title = self.title.strip()
        activity = self.activity_type.strip()
        reason = (self.justification or "").strip()
        if not self.space_id.strip() or not 1 <= len(title) <= 200 or not 1 <= len(activity) <= 60:
            raise ValueError("Informe sala, título e tipo de atividade válidos.")
        if isinstance(self.participants, bool) or not 1 <= self.participants <= 10000:
            raise ValueError("Informe entre 1 e 10000 participantes.")
        if len(reason) > 600:
            raise ValueError("A justificativa deve ter até 600 caracteres.")
        return replace(self, title=title, activity_type=activity, justification=reason or None)


@dataclass(frozen=True, slots=True)
class Reservation:
    id: str
    institution_id: str
    requester_id: str
    request: ReservationRequest
    status: ReservationStatus
    created_at: datetime
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    decision_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ReservationDetails:
    reservation: Reservation
    space_name: str
    requester_name: str
    has_overlap: bool
