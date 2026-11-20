from application.ports.space_repository import SpaceRepository
from models.domain.entities.space import Space


class SpaceService:
    """Application service for querying spaces."""

    def __init__(self, repository: SpaceRepository) -> None:
        self._repository = repository

    def list_spaces(self) -> list[Space]:
        return list(self._repository.list_all())
