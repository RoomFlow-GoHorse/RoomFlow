from typing import Protocol, Sequence

from domain.entities.space import Space


class SpaceRepository(Protocol):
    """Read-only storage contract needed by the space-list use case."""

    def list_all(self) -> Sequence[Space]: ...
