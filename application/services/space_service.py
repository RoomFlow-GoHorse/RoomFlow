import secrets
from dataclasses import replace

from application.ports.space_repository import SpaceRepository
from application.services.admin_audit_service import AdminAuditService, audited_mutation
from models.domain.entities.admin_audit_event import AdminAuditAction
from models.domain.entities.building import Building
from models.domain.entities.floor import Floor
from models.domain.entities.permission import Permission
from models.domain.entities.profile import Profile
from models.domain.entities.space import SPACE_STATUSES, Space
from models.domain.entities.user import User
from models.domain.exceptions import DuplicateResource, ResourceNotFound
from models.domain.policies.permission_policy import PermissionPolicy


class SpaceService:
    """Institution-scoped use cases for buildings, floors, and rooms."""

    def __init__(
        self,
        repository: SpaceRepository,
        permission_policy: PermissionPolicy | None = None,
        audit: AdminAuditService | None = None,
    ) -> None:
        self._repository = repository
        self._permissions = permission_policy or PermissionPolicy()
        self._audit = audit

    def list_spaces(
        self,
        actor: User | None = None,
        search: str = "",
        status: str | None = None,
        building_id: str | None = None,
        floor_id: str | None = None,
        resource_id: str | None = None,
        include_inactive: bool = False,
        *,
        room_type: str | None = None,
        min_capacity: int | None = None,
        max_capacity: int | None = None,
    ) -> list[Space]:
        if actor is None:
            return list(self._repository.list_all())
        institution_id = self._space_listing_scope(actor)
        if status is not None and status not in SPACE_STATUSES:
            raise ValueError("Status de sala inválido.")
        if min_capacity is not None and max_capacity is not None and min_capacity > max_capacity:
            raise ValueError("A capacidade mínima deve ser menor ou igual à máxima.")
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
            room_type=room_type.strip() if room_type else None,
            min_capacity=min_capacity,
            max_capacity=max_capacity,
        ))

    def location_catalog(self, actor: User) -> tuple[list[Building], list[Floor], list[Space]]:
        scope = self._permissions.authorize_listing(actor, Permission.LOCATE_SPACES)
        return (
            list(self._repository.list_buildings(scope)),
            list(self._repository.list_institution_floors(scope)),
            list(self._repository.list_spaces(scope)),
        )

    def list_buildings(self, actor: User, include_inactive: bool = False) -> list[Building]:
        institution_id = self._admin_scope(actor)
        return list(self._repository.list_buildings(institution_id, include_inactive))

    def get_building(self, actor: User, building_id: str) -> Building:
        return self._building_in_scope(actor, building_id)

    @audited_mutation
    def create_building(self, actor: User, name: str) -> Building:
        institution_id = self._admin_scope(actor)
        building = Building(f"b-{secrets.token_urlsafe(10)}", institution_id, name.strip())
        self._repository.add_building(building)
        self._record(actor, AdminAuditAction.BUILDING_CREATED, "building", building.id)
        return building

    @audited_mutation
    def update_building(self, actor: User, building_id: str, name: str) -> Building:
        building = self._building_in_scope(actor, building_id)
        updated = replace(building, name=name.strip())
        self._repository.save_building(updated)
        if updated != building:
            self._record(actor, AdminAuditAction.BUILDING_UPDATED, "building", updated.id)
        return updated

    @audited_mutation
    def deactivate_building(self, actor: User, building_id: str) -> Building:
        building = self._building_in_scope(actor, building_id)
        if self._repository.count_active_floors(building.id):
            raise ValueError("Inative os andares deste prédio antes de inativá-lo.")
        updated = replace(building, active=False)
        self._repository.save_building(updated)
        if building.active:
            self._record(actor, AdminAuditAction.BUILDING_DEACTIVATED, "building", updated.id)
        return updated

    @audited_mutation
    def activate_building(self, actor: User, building_id: str) -> Building:
        building = self._building_in_scope(actor, building_id)
        updated = replace(building, active=True)
        self._repository.save_building(updated)
        if not building.active:
            self._record(actor, AdminAuditAction.BUILDING_ACTIVATED, "building", updated.id)
        return updated

    def list_institution_floors(self, actor: User, include_inactive: bool = False) -> list[Floor]:
        return list(self._repository.list_institution_floors(self._admin_scope(actor), include_inactive))

    def list_floors(self, actor: User, building_id: str, include_inactive: bool = False) -> list[Floor]:
        building = self._building_in_scope(actor, building_id)
        return list(self._repository.list_floors(building.id, include_inactive))

    def get_floor(self, actor: User, floor_id: str) -> Floor:
        return self._floor_in_scope(actor, floor_id)

    @audited_mutation
    def create_floor(self, actor: User, building_id: str, name: str) -> Floor:
        building = self._building_in_scope(actor, building_id)
        if not building.active:
            raise ValueError("Não é possível adicionar andar a um prédio inativo.")
        floor = Floor(f"f-{secrets.token_urlsafe(10)}", building.id, name.strip())
        self._repository.add_floor(floor)
        self._record(actor, AdminAuditAction.FLOOR_CREATED, "floor", floor.id)
        return floor

    @audited_mutation
    def update_floor(self, actor: User, floor_id: str, name: str) -> Floor:
        floor = self._floor_in_scope(actor, floor_id)
        updated = replace(floor, name=name.strip())
        self._repository.save_floor(updated)
        if updated != floor:
            self._record(actor, AdminAuditAction.FLOOR_UPDATED, "floor", updated.id)
        return updated

    @audited_mutation
    def deactivate_floor(self, actor: User, floor_id: str) -> Floor:
        floor = self._floor_in_scope(actor, floor_id)
        if self._repository.count_active_spaces(floor.id):
            raise ValueError("Inative as salas deste andar antes de inativá-lo.")
        updated = replace(floor, active=False)
        self._repository.save_floor(updated)
        if floor.active:
            self._record(actor, AdminAuditAction.FLOOR_DEACTIVATED, "floor", updated.id)
        return updated

    @audited_mutation
    def activate_floor(self, actor: User, floor_id: str) -> Floor:
        floor = self._floor_in_scope(actor, floor_id)
        building = self._building_in_scope(actor, floor.building_id)
        if not building.active:
            raise ValueError("Ative o prédio antes de reativar o andar.")
        updated = replace(floor, active=True)
        self._repository.save_floor(updated)
        if not floor.active:
            self._record(actor, AdminAuditAction.FLOOR_ACTIVATED, "floor", updated.id)
        return updated

    def get_space(self, actor: User, space_id: str) -> Space:
        institution_id = self._space_listing_scope(actor)
        space = self._repository.find_space(space_id)
        if space is None or space.institution_id != institution_id:
            raise ResourceNotFound("Sala não encontrada.")
        return space

    @audited_mutation
    def create_space(
        self,
        actor: User,
        floor_id: str,
        name: str,
        room_type: str,
        capacity: int,
        status: str = "disponivel",
    ) -> Space:
        if actor.profile is Profile.MANAGER and status == "bloqueado":
            raise ValueError("Cadastre a sala e use a operação de bloqueio para informar o motivo.")
        floor = self._floor_for_space(actor, floor_id)
        building = self._building_for_space(actor, floor.building_id)
        if not floor.active or not building.active:
            raise ValueError("Não é possível cadastrar sala em prédio ou andar inativo.")
        space = self._make_space(
            f"s-{secrets.token_urlsafe(10)}", actor, building, floor,
            name, room_type, capacity, status,
        )
        space = self._repository.add_space(space)
        self._record(actor, AdminAuditAction.SPACE_CREATED, "space", space.id)
        return space

    @audited_mutation
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
        if actor.profile is Profile.MANAGER and status is not None and (
            status == "bloqueado" or (current.status == "bloqueado" and status != "inativo")
        ):
            raise ValueError("Use a operação de bloqueio ou desbloqueio da sala.")
        if not current.active and status not in {None, "inativo"}:
            raise ValueError("Reative a sala antes de alterar seu status.")
        updated = replace(
            current,
            name=name.strip() if name is not None else current.name,
            type=room_type.strip() if room_type is not None else current.type,
            capacity=capacity if capacity is not None else current.capacity,
            status=status if status is not None else current.status,
            active=current.active and status != "inativo",
        )
        if target_floor_id := floor_id or current.floor_id:
            target_floor = self._floor_for_space(actor, target_floor_id)
            building = self._building_for_space(actor, target_floor.building_id)
            if not target_floor.active or not building.active:
                raise ValueError("A sala precisa pertencer a prédio e andar ativos.")
            updated = replace(
                updated, building_id=building.id, building=building.name,
                floor_id=target_floor.id, floor=target_floor.name, location=f"{building.name}, {target_floor.name}",
            )
        self._repository.save_space(updated)
        if updated != current:
            action = AdminAuditAction.SPACE_DEACTIVATED if current.active and not updated.active else AdminAuditAction.SPACE_UPDATED
            self._record(actor, action, "space", updated.id)
        return updated

    @audited_mutation
    def block_space(self, actor: User, space_id: str, reason: str) -> Space:
        current = self.get_space(actor, space_id)
        reason = reason.strip()
        if not 1 <= len(reason) <= 500:
            raise ValueError("Informe um motivo de bloqueio com até 500 caracteres.")
        if not current.active:
            raise ValueError("Reative a sala antes de bloqueá-la.")
        if current.block_reason is not None:
            raise DuplicateResource("A sala já tem um bloqueio registrado.")
        self._repository.block_space(replace(current, status="bloqueado", block_reason=reason), actor.id)
        self._record(actor, AdminAuditAction.SPACE_BLOCKED, "space", current.id)
        return self.get_space(actor, space_id)

    @audited_mutation
    def unblock_space(self, actor: User, space_id: str) -> Space:
        current = self.get_space(actor, space_id)
        if current.status != "bloqueado":
            raise ValueError("A sala não está bloqueada.")
        self._repository.save_space(replace(current, status="disponivel", block_reason=None))
        self._record(actor, AdminAuditAction.SPACE_UNBLOCKED, "space", current.id)
        return self.get_space(actor, space_id)

    @audited_mutation
    def deactivate_space(self, actor: User, space_id: str) -> Space:
        current = self.get_space(actor, space_id)
        updated = replace(current, active=False, status="inativo")
        self._repository.save_space(updated)
        if current.active:
            self._record(actor, AdminAuditAction.SPACE_DEACTIVATED, "space", updated.id)
        return updated

    @audited_mutation
    def activate_space(self, actor: User, space_id: str) -> Space:
        current = self.get_space(actor, space_id)
        if current.floor_id:
            floor = self._floor_for_space(actor, current.floor_id)
            building = self._building_for_space(actor, floor.building_id)
            if not floor.active or not building.active:
                raise ValueError("Ative o prédio e o andar antes de reativar a sala.")
        if current.active:
            return current
        # Operational activation does not resolve a recorded block.
        keep_block = actor.profile is Profile.MANAGER and current.block_reason is not None
        updated = replace(current, active=True, status="bloqueado" if keep_block else "disponivel")
        self._repository.save_space(updated)
        self._record(actor, AdminAuditAction.SPACE_ACTIVATED, "space", updated.id)
        return updated

    def _record(self, actor: User, action: AdminAuditAction, resource_type: str, resource_id: str) -> None:
        if self._audit is not None:
            self._audit.record(actor, action, resource_type, resource_id)

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
        institution_id = self._admin_scope(actor)
        building = self._repository.find_building(building_id)
        if building is None or building.institution_id != institution_id:
            raise ResourceNotFound("Prédio não encontrado.")
        return building

    def _floor_in_scope(self, actor: User, floor_id: str) -> Floor:
        self._admin_scope(actor)
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
        self._space_listing_scope(actor)
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
