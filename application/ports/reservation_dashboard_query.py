from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ReservationDashboardMetrics:
    """Read-only results the reservation module may provide to dashboards."""

    total: int
    pending: int
    approved: int
    conflicts: int
    occupied_spaces: int
    rejected: int = 0
    cancelled: int = 0


class ReservationDashboardQuery(Protocol):
    """Small institution-scoped query contract; no reservation rules live here."""

    def get_metrics(
        self, institution_id: str, start_at: datetime, end_at: datetime,
        *, space_ids: frozenset[str] | None = None,
    ) -> ReservationDashboardMetrics: ...
