from typing import Protocol

from models.domain.entities.reservation import ReservationPeriod


class RoomBlockQuery(Protocol):
    def block_periods(
        self, institution_id: str, period: ReservationPeriod,
    ) -> dict[str, list[ReservationPeriod]]: ...
