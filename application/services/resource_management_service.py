import secrets
from dataclasses import replace

from application.ports.resource_repository import ResourceRepository
from application.ports.space_association_repository import SpaceAssociationRepository
from application.services.admin_audit_service import AdminAuditService, audited_mutation
from models.domain.entities.admin_audit_event import AdminAuditAction
from models.domain.entities.permission import Permission
from models.domain.entities.profile import Profile
from models.domain.entities.resource import Resource
from models.domain.entities.user import User
from models.domain.exceptions import ResourceNotFound
from models.domain.policies.permission_policy import PermissionPolicy


class ResourceManagementService:
    """Institution-scoped resource catalog and room-association use cases."""

    def __init__(
        self,
        resources: ResourceRepository,
        spaces: SpaceAssociationRepository,
        permission_policy: PermissionPolicy | None = None,
        audit: AdminAuditService | None = None,
    ) -> None:
        self._resources = resources
        self._spaces = spaces
        self._permissions = permission_policy or PermissionPolicy()
        self._audit = audit

    def list_resources(
        self, actor: User, search: str = "", include_inactive: bool = False
    ) -> list[Resource]:
        institution_id = self._scope(actor)
        return list(self._resources.list_resources(institution_id, search, include_inactive))

    def get_resource(self, actor: User, resource_id: str) -> Resource:
        institution_id = self._scope(actor)
        resource = self._resources.find_resource(resource_id)
        if resource is None or resource.institution_id != institution_id:
            raise ResourceNotFound("Recurso não encontrado.")
        return resource

    @audited_mutation
    def create_resource(self, actor: User, name: str) -> Resource:
        institution_id = self._scope(actor)
        normalized = " ".join(name.split())
        resource = Resource(f"res-{secrets.token_urlsafe(10)}", institution_id, normalized)
        self._resources.add_resource(resource)
        self._record(actor, AdminAuditAction.RESOURCE_CREATED, "resource", resource.id)
        return resource

    @audited_mutation
    def update_resource(self, actor: User, resource_id: str, name: str) -> Resource:
        current = self.get_resource(actor, resource_id)
        updated = replace(current, name=" ".join(name.split()))
        self._resources.save_resource(updated)
        if updated != current:
            self._record(actor, AdminAuditAction.RESOURCE_UPDATED, "resource", updated.id)
        return updated

    @audited_mutation
    def set_resource_active(self, actor: User, resource_id: str, active: bool) -> Resource:
        current = self.get_resource(actor, resource_id)
        updated = replace(current, active=active)
        self._resources.save_resource(updated)
        if current.active != updated.active:
            action = AdminAuditAction.RESOURCE_ACTIVATED if updated.active else AdminAuditAction.RESOURCE_DEACTIVATED
            self._record(actor, action, "resource", updated.id)
        return updated

    @audited_mutation
    def set_space_resources(
        self, actor: User, space_id: str, resource_ids: list[str] | tuple[str, ...]
    ):
        institution_id = self._scope(actor)
        space = self._spaces.find_space(space_id)
        if space is None or space.institution_id != institution_id:
            raise ResourceNotFound("Sala não encontrada.")
        unique_ids = tuple(dict.fromkeys(resource_ids))
        if len(unique_ids) != len(resource_ids):
            raise ValueError("A lista contém recursos repetidos.")
        selected = []
        for resource_id in unique_ids:
            resource = self._resources.find_resource(resource_id)
            if (
                resource is None or resource.institution_id != institution_id
                or (not resource.active and resource_id not in space.resource_ids)
            ):
                raise ResourceNotFound("Um dos recursos não está disponível nesta instituição.")
            selected.append(resource)
        updated = replace(
            space,
            resource_ids=tuple(item.id for item in selected),
            resources=tuple(item.name for item in selected),
        )
        self._spaces.save_space(updated)
        if updated.resource_ids != space.resource_ids:
            self._record(actor, AdminAuditAction.SPACE_RESOURCES_UPDATED, "space", updated.id)
        return updated

    def _record(self, actor: User, action: AdminAuditAction, resource_type: str, resource_id: str) -> None:
        if self._audit is not None:
            self._audit.record(actor, action, resource_type, resource_id)

    def _scope(self, actor: User) -> str:
        permission = (
            Permission.MANAGE_FLOOR_PLAN
            if actor.profile is Profile.ADMIN
            else Permission.MANAGE_SPACES
        )
        return self._permissions.authorize_listing(actor, permission)
