from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Space:
    """Read model for the space fields already represented in the UI mocks."""

    id: str
    name: str
    type: str
    capacity: int
    building: str
    floor: str
    location: str
    status: str
    resources: tuple[str, ...]
    occupancy: int
