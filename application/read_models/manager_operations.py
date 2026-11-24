from collections import Counter
from dataclasses import dataclass
from datetime import date, time

from application.ports.reservation_dashboard_query import ReservationDashboardMetrics
from models.domain.entities.building import Building
from models.domain.entities.reservation import ReservationDetails
from models.domain.entities.space import Space


@dataclass(frozen=True, slots=True)
class ManagerOperationsContext:
    timezone: str
    today: date
    opens_at: time
    closes_at: time
    spaces: tuple[Space, ...]
    buildings: tuple[Building, ...]


@dataclass(frozen=True, slots=True)
class RoomOccupancy:
    room: Space
    status: str
    usable_seconds: float
    occupied_seconds: float
    blocked_seconds: float

    @property
    def rate(self) -> float:
        return self.occupied_seconds / self.usable_seconds if self.usable_seconds else 0.0


@dataclass(frozen=True, slots=True)
class ManagerOperations:
    timezone: str
    start_date: date
    end_date: date
    opens_at: time
    closes_at: time
    metrics: ReservationDashboardMetrics
    spaces: tuple[RoomOccupancy, ...]
    reservations: tuple[ReservationDetails, ...]

    @property
    def occupancy_rate(self) -> float:
        usable = sum(item.usable_seconds for item in self.spaces)
        return sum(item.occupied_seconds for item in self.spaces) / usable if usable else 0.0

    @property
    def space_counts(self) -> dict[str, int]:
        counts = Counter(room.status for room in self.spaces)
        return {
            "available": counts["disponivel"], "occupied": counts["ocupado"], "blocked": counts["bloqueado"],
            "inactive": counts["inativo"], "unavailable": counts["indisponivel"], "total": len(self.spaces),
        }
