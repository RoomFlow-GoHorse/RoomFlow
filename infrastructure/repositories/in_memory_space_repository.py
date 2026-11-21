from collections.abc import Sequence
from dataclasses import replace
from threading import RLock

from infrastructure.in_memory_admin_transaction import InMemoryAdminTransaction
from models.domain.entities.building import Building
from models.domain.entities.floor import Floor
from models.domain.entities.floor_plan import FloorPlan, RoomPosition
from models.domain.entities.resource import Resource
from models.domain.entities.space import Space
from models.domain.exceptions import DuplicateResource, ResourceNotFound


class InMemorySpaceRepository:
    """Temporary process-local store for the physical structure."""

    def __init__(
        self,
        spaces: Sequence[Space] | None = None,
        buildings: Sequence[Building] | None = None,
        floors: Sequence[Floor] | None = None,
        resources: Sequence[Resource] | None = None,
        floor_plans: Sequence[FloorPlan] | None = None,
        *,
        transaction: InMemoryAdminTransaction | None = None,
    ) -> None:
        self._lock = transaction.lock if transaction is not None else RLock()
        if spaces is None:
            (
                self._buildings,
                self._floors,
                self._spaces,
                self._resources,
                self._floor_plans,
            ) = self._demo_structure()
        else:
            self._spaces = {item.id: item for item in spaces}
            self._buildings = {item.id: item for item in (buildings or ())}
            self._floors = {item.id: item for item in (floors or ())}
            self._resources = {item.id: item for item in (resources or ())}
            self._floor_plans = {item.id: item for item in (floor_plans or ())}
        if transaction is not None:
            transaction.register(self._spaces, self._buildings, self._floors, self._resources, self._floor_plans)

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
        resource_id: str | None = None,
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
                if resource_id and resource_id not in item.resource_ids:
                    continue
                if query and query not in " ".join((item.name, item.type, item.building, item.floor, item.location)).casefold():
                    continue
                items.append(item)
            return tuple(sorted(items, key=lambda item: (item.building.casefold(), self._floor_order(item.floor), item.name.casefold())))

    def find_space(self, space_id: str) -> Space | None:
        with self._lock:
            return self._spaces.get(space_id)

    def add_space(self, space: Space) -> Space:
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
            return space

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
            current = self._spaces[space.id]
            if current.floor_id != space.floor_id or (current.active and not space.active):
                self._remove_room_positions(current.floor_id, space.id)
            self._spaces[space.id] = space

    def list_resources(
        self, institution_id: str, search: str = "", include_inactive: bool = False
    ) -> tuple[Resource, ...]:
        query = search.strip().casefold()
        with self._lock:
            rows = (
                item for item in self._resources.values()
                if item.institution_id == institution_id
                and (include_inactive or item.active)
                and (not query or query in item.name.casefold())
            )
            return tuple(sorted(rows, key=lambda item: item.name.casefold()))

    def find_resource(self, resource_id: str) -> Resource | None:
        with self._lock:
            return self._resources.get(resource_id)

    def add_resource(self, resource: Resource) -> Resource:
        with self._lock:
            self._assert_unique_name(
                resource.name,
                (item.name for item in self._resources.values()
                 if item.institution_id == resource.institution_id),
                "Já existe um recurso com esse nome na instituição.",
            )
            if resource.id in self._resources:
                raise DuplicateResource("O identificador do recurso já está em uso.")
            self._resources[resource.id] = resource
            return resource

    def save_resource(self, resource: Resource) -> None:
        with self._lock:
            current = self._resources.get(resource.id)
            if current is None:
                raise ResourceNotFound("Recurso não encontrado.")
            if resource.institution_id != current.institution_id:
                raise ValueError("Não é permitido transferir um recurso para outra instituição.")
            self._assert_unique_name(
                resource.name,
                (item.name for key, item in self._resources.items()
                 if key != resource.id and item.institution_id == resource.institution_id),
                "Já existe um recurso com esse nome na instituição.",
            )
            self._resources[resource.id] = resource
            for space_id, space in tuple(self._spaces.items()):
                if resource.id in space.resource_ids:
                    names = tuple(
                        resource.name if item_id == resource.id else self._resources[item_id].name
                        for item_id in space.resource_ids
                    )
                    self._spaces[space_id] = replace(space, resources=names)

    def find_floor_plan_by_floor(self, floor_id: str) -> FloorPlan | None:
        with self._lock:
            return next((item for item in self._floor_plans.values() if item.floor_id == floor_id), None)

    def find_floor_plan(self, plan_id: str) -> FloorPlan | None:
        with self._lock:
            return self._floor_plans.get(plan_id)

    def save_floor_plan(self, plan: FloorPlan) -> None:
        with self._lock:
            existing = self._floor_plans.get(plan.id)
            floor = self._floors.get(plan.floor_id)
            building = self._buildings.get(plan.building_id)
            if (
                floor is None or building is None or floor.building_id != building.id
                or building.institution_id != plan.institution_id
            ):
                raise ResourceNotFound("O andar ou prédio da planta não pertence à instituição.")
            other = next(
                (item for item in self._floor_plans.values()
                 if item.floor_id == plan.floor_id and item.id != plan.id),
                None,
            )
            if other:
                raise DuplicateResource("Este andar já possui uma planta cadastrada.")
            for position in plan.positions:
                space = self._spaces.get(position.space_id)
                if (
                    space is None or space.institution_id != plan.institution_id
                    or space.floor_id != plan.floor_id or not space.active
                ):
                    raise ResourceNotFound("A posição referencia uma sala inválida para este andar.")
            if existing and existing.floor_id != plan.floor_id:
                raise ValueError("A planta não pode ser transferida para outro andar.")
            self._floor_plans[plan.id] = plan

    def remove_floor_plan(self, floor_id: str) -> FloorPlan | None:
        with self._lock:
            plan = next((item for item in self._floor_plans.values() if item.floor_id == floor_id), None)
            if plan:
                self._floor_plans.pop(plan.id, None)
            return plan

    def _remove_room_positions(self, floor_id: str, space_id: str) -> None:
        plan = next((item for item in self._floor_plans.values() if item.floor_id == floor_id), None)
        if plan:
            positions = tuple(item for item in plan.positions if item.space_id != space_id)
            if positions != plan.positions:
                self._floor_plans[plan.id] = replace(plan, positions=positions)

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
        if len(space.resource_ids) != len(set(space.resource_ids)):
            raise ValueError("A sala não pode repetir recursos associados.")
        if space.resource_ids:
            selected = [self._resources.get(item_id) for item_id in space.resource_ids]
            if any(item is None or item.institution_id != space.institution_id for item in selected):
                raise ResourceNotFound("Um dos recursos não pertence à instituição da sala.")
            expected_names = tuple(item.name for item in selected if item is not None)
            if expected_names != space.resources:
                raise ValueError("Os nomes e identificadores dos recursos da sala não correspondem.")

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
        resource_names = sorted({name for space in spaces for name in space.resources}, key=str.casefold)
        resources = tuple(
            Resource(f"res-{index}", "inst-demo", name)
            for index, name in enumerate(resource_names, start=1)
        )
        resource_ids = {item.name.casefold(): item.id for item in resources}
        spaces = tuple(
            replace(
                item,
                resource_ids=tuple(resource_ids[name.casefold()] for name in item.resources),
            )
            for item in spaces
        )
        return (
            {item.id: item for item in buildings},
            {item.id: item for item in floors},
            {item.id: item for item in spaces},
            {item.id: item for item in resources},
            {},
        )
