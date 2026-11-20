from collections.abc import Sequence
from dataclasses import replace
from threading import RLock

from models.domain.entities.building import Building
from models.domain.entities.floor import Floor
from models.domain.entities.space import Space
from models.domain.exceptions import DuplicateResource, ResourceNotFound


class InMemorySpaceRepository:
    """Temporary process-local store for the physical structure."""

    def __init__(
        self,
        spaces: Sequence[Space] | None = None,
        buildings: Sequence[Building] | None = None,
        floors: Sequence[Floor] | None = None,
    ) -> None:
        self._lock = RLock()
        if spaces is None:
            self._buildings, self._floors, self._spaces = self._demo_structure()
        else:
            self._spaces = {item.id: item for item in spaces}
            self._buildings = {item.id: item for item in (buildings or ())}
            self._floors = {item.id: item for item in (floors or ())}

    def list_all(self) -> tuple[Space, ...]:
        with self._lock:
            return tuple(self._spaces.values())

    def list_buildings(self, institution_id: str, include_inactive: bool = False) -> tuple[Building, ...]:
        with self._lock:
            values = (
                item for item in self._buildings.values()
                if item.institution_id == institution_id and (include_inactive or item.active)
            )
            return tuple(sorted(values, key=lambda item: item.name.casefold()))

    def find_building(self, building_id: str) -> Building | None:
        with self._lock:
            return self._buildings.get(building_id)

    def add_building(self, building: Building) -> None:
        with self._lock:
            self._assert_unique_name(
                building.name,
                (item.name for item in self._buildings.values() if item.institution_id == building.institution_id),
                "Já existe um prédio com esse nome na instituição.",
            )
            if building.id in self._buildings:
                raise DuplicateResource("O identificador do prédio já está em uso.")
            self._buildings[building.id] = building

    def save_building(self, building: Building) -> None:
        with self._lock:
            current = self._buildings.get(building.id)
            if current is None:
                raise ResourceNotFound("Prédio não encontrado.")
            if building.institution_id != current.institution_id:
                raise ValueError("Não é permitido transferir um prédio para outra instituição.")
            if not building.active and any(
                item.active for item in self._floors.values() if item.building_id == building.id
            ):
                raise ValueError("Inative os andares deste prédio antes de inativá-lo.")
            self._assert_unique_name(
                building.name,
                (item.name for key, item in self._buildings.items()
                 if key != building.id and item.institution_id == building.institution_id),
                "Já existe um prédio com esse nome na instituição.",
            )
            self._buildings[building.id] = building
            for space_id, space in tuple(self._spaces.items()):
                if space.building_id == building.id:
                    self._spaces[space_id] = replace(
                        space,
                        building=building.name,
                        location=f"{building.name}, {space.floor}",
                    )

    def list_floors(self, building_id: str, include_inactive: bool = False) -> tuple[Floor, ...]:
        with self._lock:
            values = (
                item for item in self._floors.values()
                if item.building_id == building_id and (include_inactive or item.active)
            )
            return tuple(sorted(values, key=lambda item: (self._floor_order(item.name), item.name.casefold())))

    def find_floor(self, floor_id: str) -> Floor | None:
        with self._lock:
            return self._floors.get(floor_id)

    def add_floor(self, floor: Floor) -> None:
        with self._lock:
            building = self._buildings.get(floor.building_id)
            if building is None or not building.active:
                raise ResourceNotFound("Prédio ativo não encontrado.")
            self._assert_unique_name(
                floor.name,
                (item.name for item in self._floors.values() if item.building_id == floor.building_id),
                "Já existe um andar com esse nome no prédio.",
            )
            if floor.id in self._floors:
                raise DuplicateResource("O identificador do andar já está em uso.")
            self._floors[floor.id] = floor

    def save_floor(self, floor: Floor) -> None:
        with self._lock:
            current = self._floors.get(floor.id)
            if current is None:
                raise ResourceNotFound("Andar não encontrado.")
            if floor.building_id != current.building_id:
                raise ValueError("Não é permitido transferir um andar para outro prédio.")
            building = self._buildings.get(floor.building_id)
            if building is None or (floor.active and not building.active):
                raise ValueError("O andar deve pertencer a um prédio ativo.")
            if not floor.active and any(
                item.active and item.status != "inativo"
                for item in self._spaces.values() if item.floor_id == floor.id
            ):
                raise ValueError("Inative as salas deste andar antes de inativá-lo.")
            self._assert_unique_name(
                floor.name,
                (item.name for key, item in self._floors.items()
                 if key != floor.id and item.building_id == floor.building_id),
                "Já existe um andar com esse nome no prédio.",
            )
            self._floors[floor.id] = floor
            building = self._buildings[floor.building_id]
            for space_id, space in tuple(self._spaces.items()):
                if space.floor_id == floor.id:
                    self._spaces[space_id] = replace(
                        space,
                        floor=floor.name,
                        building=building.name,
                        location=f"{building.name}, {floor.name}",
                    )

    def list_spaces(
        self,
        institution_id: str,
        search: str = "",
        status: str | None = None,
        building_id: str | None = None,
        floor_id: str | None = None,
        include_inactive: bool = False,
    ) -> tuple[Space, ...]:
        query = search.strip().casefold()
        with self._lock:
            items = []
            for item in self._spaces.values():
                if item.institution_id != institution_id:
                    continue
                if not include_inactive and (not item.active or item.status == "inativo"):
                    continue
                if status and item.status != status:
                    continue
                if building_id and item.building_id != building_id:
                    continue
                if floor_id and item.floor_id != floor_id:
                    continue
                if query and query not in " ".join((item.name, item.type, item.building, item.floor, item.location)).casefold():
                    continue
                items.append(item)
            return tuple(sorted(items, key=lambda item: (item.building.casefold(), self._floor_order(item.floor), item.name.casefold())))

    def find_space(self, space_id: str) -> Space | None:
        with self._lock:
            return self._spaces.get(space_id)

    def add_space(self, space: Space) -> None:
        with self._lock:
            self._assert_space_relationship(space)
            self._assert_unique_name(
                space.name,
                (item.name for item in self._spaces.values() if item.floor_id == space.floor_id),
                "Já existe uma sala com esse nome neste andar.",
            )
            if space.id in self._spaces:
                raise DuplicateResource("O identificador da sala já está em uso.")
            self._spaces[space.id] = space

    def save_space(self, space: Space) -> None:
        with self._lock:
            if space.id not in self._spaces:
                raise ResourceNotFound("Sala não encontrada.")
            self._assert_space_relationship(space)
            self._assert_unique_name(
                space.name,
                (item.name for key, item in self._spaces.items()
                 if key != space.id and item.floor_id == space.floor_id),
                "Já existe uma sala com esse nome neste andar.",
            )
            self._spaces[space.id] = space

    def _assert_space_relationship(self, space: Space) -> None:
        floor = self._floors.get(space.floor_id)
        building = self._buildings.get(space.building_id)
        if (
            floor is None or building is None
            or floor.building_id != building.id
            or building.institution_id != space.institution_id
        ):
            raise ResourceNotFound("O prédio ou andar informado não pertence à instituição da sala.")
        if space.active and (not floor.active or not building.active):
            raise ValueError("Uma sala ativa precisa pertencer a prédio e andar ativos.")

    def count_active_floors(self, building_id: str) -> int:
        with self._lock:
            return sum(item.active for item in self._floors.values() if item.building_id == building_id)

    def count_active_spaces(self, floor_id: str) -> int:
        with self._lock:
            return sum(
                item.active and item.status != "inativo"
                for item in self._spaces.values() if item.floor_id == floor_id
            )

    @staticmethod
    def _assert_unique_name(name: str, names, message: str) -> None:
        normalized = name.strip().casefold()
        if any(existing.strip().casefold() == normalized for existing in names):
            raise DuplicateResource(message)

    @staticmethod
    def _floor_order(name: str) -> int:
        order = {"Subsolo": 0, "Térreo": 1, "Mezanino": 2}
        normalized = name.casefold()
        if normalized in {"térreo", "terreo"}:
            return 1
        for number in range(1, 21):
            if normalized in {f"{number}º andar", f"{number}o andar", f"{number}º pavimento"}:
                return number + 2
        if normalized == "subsolo":
            return order["Subsolo"]
        if normalized == "mezanino":
            return order["Mezanino"]
        return 100

    @staticmethod
    def _demo_structure():
        buildings = (
            Building("b-1", "inst-demo", "Bloco A"),
            Building("b-2", "inst-demo", "Bloco B"),
            Building("b-3", "inst-demo", "Bloco C"),
            Building("b-4", "inst-demo", "Bloco D"),
        )
        floor_rows = (
            ("b-1-f-1", "b-1", "Térreo"), ("b-1-f-2", "b-1", "1º andar"),
            ("b-1-f-3", "b-1", "2º andar"), ("b-2-f-1", "b-2", "Térreo"),
            ("b-2-f-2", "b-2", "2º andar"), ("b-3-f-1", "b-3", "Térreo"),
            ("b-4-f-1", "b-4", "Térreo"),
        )
        floors = tuple(Floor(*row) for row in floor_rows)
        floor_ids = { (floor.building_id, floor.name): floor.id for floor in floors }
        source = (
            ("s1", "Sala 101", "Sala de aula", 20, "Bloco A", "1º andar", "disponivel", ("Projetor", "Quadro branco"), 64),
            ("s2", "Sala 204", "Sala de aula", 30, "Bloco B", "2º andar", "ocupado", ("TV", "Ar-condicionado"), 78),
            ("s3", "Auditório Principal", "Auditório", 150, "Bloco A", "Térreo", "disponivel", ("Áudio", "Microfones", "Projetor"), 52),
            ("s4", "Laboratório de Informática", "Laboratório", 40, "Bloco C", "Térreo", "disponivel", ("Computadores", "Projetor"), 71),
            ("s5", "Auditório A", "Auditório", 80, "Bloco D", "Térreo", "bloqueado", ("Áudio",), 12),
            ("s6", "Sala de Reuniões B", "Sala de reuniões", 8, "Bloco A", "1º andar", "disponivel", ("Videoconferência",), 46),
        )
        building_ids = {item.name: item.id for item in buildings}
        spaces = tuple(
            Space(
                id, name, room_type, capacity, building_name, floor_name,
                f"{building_name}, {floor_name}", status, resources, occupancy,
                "inst-demo", building_ids[building_name], floor_ids[(building_ids[building_name], floor_name)],
            )
            for id, name, room_type, capacity, building_name, floor_name, status, resources, occupancy in source
        )
        return (
            {item.id: item for item in buildings},
            {item.id: item for item in floors},
            {item.id: item for item in spaces},
        )
