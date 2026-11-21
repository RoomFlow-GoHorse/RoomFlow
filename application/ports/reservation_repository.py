from typing import Protocol

from models.domain.entities.reservation import Reservation, ReservationDetails, ReservationPeriod


class ReservationRepository(Protocol):
    def add(self, reservation: Reservation) -> ReservationDetails: ...

    def save(self, reservation: Reservation) -> ReservationDetails: ...

    def find(
        self, institution_id: str, reservation_id: str, requester_id: str | None = None,
    ) -> ReservationDetails | None: ...

    def list(self, institution_id: str, requester_id: str | None = None) -> list[ReservationDetails]: ...

    def overlapping_spaces(
        self, institution_id: str, period: ReservationPeriod, *,
        approved_only: bool, space_id: str | None = None, exclude_id: str | None = None,
        requester_id: str | None = None,
    ) -> set[str]: ...
