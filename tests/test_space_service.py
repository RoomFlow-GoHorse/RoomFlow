import unittest

from application.services.space_service import SpaceService
from models.domain.entities.space import Space
from infrastructure.repositories.in_memory_space_repository import (
    InMemorySpaceRepository,
)


class StubSpaceRepository:
    def __init__(self, spaces: tuple[Space, ...]) -> None:
        self.spaces = spaces

    def list_all(self) -> tuple[Space, ...]:
        return self.spaces


class SpaceServiceTests(unittest.TestCase):
    def test_lists_spaces_from_injected_repository(self) -> None:
        expected = (
            Space(
                "s-test", "Sala de teste", "Sala", 10, "Bloco X", "Térreo",
                "Bloco X, Térreo", "disponivel", (), 0,
            ),
        )
        service = SpaceService(StubSpaceRepository(expected))

        self.assertEqual(service.list_spaces(), list(expected))

    def test_demo_repository_is_temporary_and_has_seed_data(self) -> None:
        spaces = SpaceService(InMemorySpaceRepository()).list_spaces()

        self.assertEqual(len(spaces), 6)
        self.assertEqual(spaces[0].id, "s1")
        self.assertEqual(spaces[0].name, "Sala 101")


if __name__ == "__main__":
    unittest.main()
