
from threading import RLock

from models.domain.entities.reservation_type import ReservationType
from models.domain.exceptions import DuplicateResource, ResourceNotFound


class InMemoryReservationTypeRepository:
    """In-memory repository for institution-scoped reservation types."""

    def __init__(self, transaction=None) -> None:
        self._lock = transaction.lock if transaction else RLock()
        self._types: dict[str, ReservationType] = {}

        if transaction is not None:
            transaction.register(self._types)

    def list_types(
        self,
        institution_id: str,
        include_inactive: bool = False,
    ) -> list[ReservationType]:
        with self._lock:
            items = [
                item
                for item in self._types.values()
                if item.institution_id == institution_id
                and (include_inactive or item.active)
            ]

            return sorted(items, key=lambda item: item.name.casefold())

    def find_type(self, type_id: str) -> ReservationType | None:
        with self._lock:
            return self._types.get(type_id)

    def add_type(self, reservation_type: ReservationType) -> ReservationType:
        with self._lock:
            if reservation_type.id in self._types:
                raise DuplicateResource("Tipo de reserva já cadastrado.")

            self._ensure_unique_name(
                reservation_type.institution_id,
                reservation_type.name,
            )

            self._types[reservation_type.id] = reservation_type
            return reservation_type

    def save_type(self, reservation_type: ReservationType) -> None:
        with self._lock:
            current = self._types.get(reservation_type.id)

            if current is None:
                raise ResourceNotFound("Tipo de reserva não encontrado.")

            if current.institution_id != reservation_type.institution_id:
                raise ValueError(
                    "Não é permitido transferir um tipo para outra instituição."
                )

            self._ensure_unique_name(
                reservation_type.institution_id,
                reservation_type.name,
                exclude_id=reservation_type.id,
            )

            self._types[reservation_type.id] = reservation_type

    def _ensure_unique_name(
        self,
        institution_id: str,
        name: str,
        exclude_id: str | None = None,
    ) -> None:
        normalized_name = name.strip().casefold()

        for item in self._types.values():
            if (
                item.institution_id == institution_id
                and item.id != exclude_id
                and item.name.strip().casefold() == normalized_name
            ):
                raise DuplicateResource(
                    "Já existe um tipo de reserva com esse nome."
                )
