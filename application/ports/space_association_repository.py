from typing import Protocol

from models.domain.entities.space import Space


class SpaceAssociationRepository(Protocol):
    def find_space(self, space_id: str) -> Space | None: ...
    def save_space(self, space: Space) -> None: ...
