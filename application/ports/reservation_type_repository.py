
from typing import Protocol, Sequence

from models.domain.entities.reservation_type import ReservationType


class ReservationTypeRepository(Protocol):
    def list_types(
        self,
        institution_id: str,
        include_inactive: bool = False,
    ) -> Sequence[ReservationType]: ...

    def find_type(self, type_id: str) -> ReservationType | None: ...

    def add_type(self, reservation_type: ReservationType) -> ReservationType: ...

    def save_type(self, reservation_type: ReservationType) -> None: ...
