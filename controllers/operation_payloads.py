"""Input validation shared by local and optional HTTP controllers."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from models.domain.entities.reservation import ReservationRequest, ReservationPeriod, ReservationStatus
from models.domain.entities.reservation_conflict import ConflictAction


class ReservationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    space_id: str = Field(min_length=1, max_length=19)
    title: str = Field(min_length=1, max_length=200)
    activity_type: str = Field(min_length=1, max_length=60)
    start: datetime
    end: datetime
    participants: int = Field(strict=True, ge=1, le=10000)
    justification: str | None = Field(default=None, max_length=600)

    def to_request(self) -> ReservationRequest:
        return ReservationRequest(
            self.space_id, self.title, self.activity_type, ReservationPeriod(self.start, self.end),
            self.participants, self.justification,
        )


class DecisionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ReservationStatus
    reason: str | None = Field(default=None, max_length=600)


class ReservationEditPayload(ReservationPayload):
    reason: str | None = Field(default=None, max_length=600)


class CancellationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=600)


class ResolutionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ConflictAction
    reason: str = Field(min_length=1, max_length=600)
    reservation_id: str | None = Field(default=None, min_length=1, max_length=19)
    space_id: str | None = Field(default=None, min_length=1, max_length=19)
