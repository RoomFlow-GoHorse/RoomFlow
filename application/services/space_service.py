import secrets
from dataclasses import replace

from application.ports.space_repository import SpaceRepository
from models.domain.entities.building import Building
from models.domain.entities.floor import Floor
from models.domain.entities.permission import Permission
from models.domain.entities.profile import Profile
from models.domain.entities.space import SPACE_STATUSES, Space
from models.domain.entities.user import User
from models.domain.exceptions import ResourceNotFound
from models.domain.policies.permission_policy import PermissionPolicy


class SpaceService:
    """Institution-scoped use cases for buildings, floors, and rooms."""

    def __init__(
        self,
        repository: SpaceRepository,
        permission_policy: PermissionPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._permissions = permission_policy or PermissionPolicy()

    def list_spaces(
        self,
        actor: User | None = None,
        search: str = "",
        status: str | None = None,
        building_id: str | None = None,
        floor_id: str | None = None,
        resource_id: str | None = None,
        include_inactive: bool = False,
    ) -> list[Space]:
        if actor is None:
            return list(self._repository.list_all())
        institution_id = self._space_listing_scope(actor)
        if status is not None and status not in SPACE_STATUSES:
            raise ValueError("Status de sala inválido.")
        if building_id:
            building = self._building_for_space(actor, building_id)
        else:
            building = None
        if floor_id:
            floor = self._floor_for_space(actor, floor_id)
            if building_id and floor.building_id != building.id:
                raise ResourceNotFound("Andar não encontrado.")
        return list(self._repository.list_spaces(
            institution_id,
            search=search,
            status=status,
            building_id=building_id,
            floor_id=floor_id,
            resource_id=resource_id,
            include_inactive=include_inactive,
        ))

    def list_buildings(self, actor: User, include_inactive: bool = False) -> list[Building]:
        institution_id = self._admin_scope(actor)
        return list(self._repository.list_buildings(institution_id, include_inactive))

    def get_building(self, actor: User, building_id: str) -> Building:
        return self._building_in_scope(actor, building_id)

    def create_building(self, actor: User, name: str) -> Building:
        institution_id = self._admin_scope(actor)
        building = Building(f"b-{secrets.token_urlsafe(10)}", institution_id, name.strip())
        self._repository.add_building(building)
        return building

    def update_building(self, actor: User, building_id: str, name: str) -> Building:
        building = self._building_in_scope(actor, building_id)
        updated = replace(building, name=name.strip())
        self._repository.save_building(updated)
        return updated

    def deactivate_building(self, actor: User, building_id: str) -> Building:
        building = self._building_in_scope(actor, building_id)
        if self._repository.count_active_floors(building.id):
            raise ValueError("Inative os andares deste prédio antes de inativá-lo.")
        updated = replace(building, active=False)
        self._repository.save_building(updated)
        return updated

    def activate_building(self, actor: User, building_id: str) -> Building:
        building = self._building_in_scope(actor, building_id)
        updated = replace(building, active=True)
        self._repository.save_building(updated)
        return updated

    def list_floors(self, actor: User, building_id: str, include_inactive: bool = False) -> list[Floor]:
        building = self._building_in_scope(actor, building_id)
        return list(self._repository.list_floors(building.id, include_inactive))

    def get_floor(self, actor: User, floor_id: str) -> Floor:
        return self._floor_in_scope(actor, floor_id)

    def create_floor(self, actor: User, building_id: str, name: str) -> Floor:
        building = self._building_in_scope(actor, building_id)
        if not building.active:
            raise ValueError("Não é possível adicionar andar a um prédio inativo.")
        floor = Floor(f"f-{secrets.token_urlsafe(10)}", building.id, name.strip())
        self._repository.add_floor(floor)
        return floor

    def update_floor(self, actor: User, floor_id: str, name: str) -> Floor:
        floor = self._floor_in_scope(actor, floor_id)
        updated = replace(floor, name=name.strip())
        self._repository.save_floor(updated)
        return updated

    def deactivate_floor(self, actor: User, floor_id: str) -> Floor:
        floor = self._floor_in_scope(actor, floor_id)
        if self._repository.count_active_spaces(floor.id):
            raise ValueError("Inative as salas deste andar antes de inativá-lo.")
        updated = replace(floor, active=False)
        self._repository.save_floor(updated)
        return updated

    def activate_floor(self, actor: User, floor_id: str) -> Floor:
        floor = self._floor_in_scope(actor, floor_id)
        building = self._building_in_scope(actor, floor.building_id)
        if not building.active:
            raise ValueError("Ative o prédio antes de reativar o andar.")
        updated = replace(floor, active=True)
        self._repository.save_floor(updated)
        return updated

    def get_space(self, actor: User, space_id: str) -> Space:
        space = self._repository.find_space(space_id)
        if space is None or space.institution_id != self._space_listing_scope(actor):
            raise ResourceNotFound("Sala não encontrada.")
        return space

    def create_space(
        self,
        actor: User,
        floor_id: str,
        name: str,
        room_type: str,
        capacity: int,
        status: str = "disponivel",
    ) -> Space:
        floor = self._floor_for_space(actor, floor_id)
        building = self._building_for_space(actor, floor.building_id)
        if not floor.active or not building.active:
            raise ValueError("Não é possível cadastrar sala em prédio ou andar inativo.")
        space = self._make_space(
            f"s-{secrets.token_urlsafe(10)}", actor, building, floor,
            name, room_type, capacity, status,
        )
        self._repository.add_space(space)
        return space

    def update_space(
        self,
        actor: User,
        space_id: str,
        name: str | None = None,
        room_type: str | None = None,
        capacity: int | None = None,
        status: str | None = None,
        floor_id: str | None = None,
    ) -> Space:
        current = self.get_space(actor, space_id)
        if not current.active and status not in {None, "inativo"}:
            raise ValueError("Reative a sala antes de alterar seu status.")
        target_floor = self._floor_for_space(actor, floor_id or current.floor_id)
        building = self._building_for_space(actor, target_floor.building_id)
        if not target_floor.active or not building.active:
            raise ValueError("A sala precisa pertencer a prédio e andar ativos.")
        updated = self._make_space(
            current.id, actor, building, target_floor,
            name if name is not None else current.name,
            room_type if room_type is not None else current.type,
            capacity if capacity is not None else current.capacity,
            status if status is not None else current.status,
            active=current.active,
            resources=current.resources,
            resource_ids=current.resource_ids,
            occupancy=current.occupancy,
        )
        self._repository.save_space(updated)
        return updated

    def deactivate_space(self, actor: User, space_id: str) -> Space:
        current = self.get_space(actor, space_id)
        updated = replace(current, active=False, status="inativo")
        self._repository.save_space(updated)
        return updated

    def activate_space(self, actor: User, space_id: str) -> Space:
        current = self.get_space(actor, space_id)
        floor = self._floor_for_space(actor, current.floor_id)
        building = self._building_for_space(actor, floor.building_id)
        if not floor.active or not building.active:
            raise ValueError("Ative o prédio e o andar antes de reativar a sala.")
        updated = replace(current, active=True, status="disponivel")
        self._repository.save_space(updated)
        return updated

    def _admin_scope(self, actor: User) -> str:
        return self._permissions.authorize_listing(actor, Permission.MANAGE_FLOOR_PLAN)

    def _space_listing_scope(self, actor: User) -> str:
        permission = (
            Permission.MANAGE_FLOOR_PLAN
            if actor.profile is Profile.ADMIN
            else Permission.MANAGE_SPACES
        )
        return self._permissions.authorize_listing(actor, permission)

    def _building_in_scope(self, actor: User, building_id: str) -> Building:
        building = self._repository.find_building(building_id)
        if building is None or building.institution_id != self._admin_scope(actor):
            raise ResourceNotFound("Prédio não encontrado.")
        return building

    def _floor_in_scope(self, actor: User, floor_id: str) -> Floor:
        floor = self._repository.find_floor(floor_id)
        if floor is None:
            raise ResourceNotFound("Andar não encontrado.")
        self._building_in_scope(actor, floor.building_id)
        return floor

    def _building_for_space(self, actor: User, building_id: str) -> Building:
        building = self._repository.find_building(building_id)
        if building is None or building.institution_id != self._space_listing_scope(actor):
            raise ResourceNotFound("Prédio não encontrado.")
        return building

    def _floor_for_space(self, actor: User, floor_id: str) -> Floor:
        floor = self._repository.find_floor(floor_id)
        if floor is None:
            raise ResourceNotFound("Andar não encontrado.")
        self._building_for_space(actor, floor.building_id)
        return floor

    @staticmethod
    def _make_space(
        space_id: str,
        actor: User,
        building: Building,
        floor: Floor,
        name: str,
        room_type: str,
        capacity: int,
        status: str,
        active: bool = True,
        resources: tuple[str, ...] = (),
        resource_ids: tuple[str, ...] = (),
        occupancy: int = 0,
    ) -> Space:
        if status not in SPACE_STATUSES:
            raise ValueError("Status de sala inválido.")
        if status == "inativo":
            active = False
        return Space(
            id=space_id,
            name=name.strip(),
            type=room_type.strip(),
            capacity=capacity,
            building=building.name,
            floor=floor.name,
            location=f"{building.name}, {floor.name}",
            status=status,
            resources=resources,
            resource_ids=resource_ids,
            occupancy=occupancy,
            institution_id=actor.institution_id or "",
            building_id=building.id,
            floor_id=floor.id,
            active=active,
        )
