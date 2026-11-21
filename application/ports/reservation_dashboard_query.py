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


class ReservationDashboardQuery(Protocol):
    """Small institution-scoped query contract; no reservation rules live here."""

    def get_metrics(
        self, institution_id: str, start_at: datetime, end_at: datetime
    ) -> ReservationDashboardMetrics: ...
