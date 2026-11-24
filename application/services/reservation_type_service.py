
import secrets
from dataclasses import replace

from application.ports.reservation_type_repository import ReservationTypeRepository
from application.services.admin_audit_service import AdminAuditService, audited_mutation
from models.domain.entities.admin_audit_event import AdminAuditAction
from models.domain.entities.permission import Permission
from models.domain.entities.reservation_type import ReservationType
from models.domain.entities.user import User
from models.domain.exceptions import ResourceNotFound
from models.domain.policies.permission_policy import PermissionPolicy


class ReservationTypeService:
    """Institution-scoped reservation type management."""

    def __init__(
        self,
        repository: ReservationTypeRepository,
        permission_policy: PermissionPolicy | None = None,
        audit: AdminAuditService | None = None,
    ) -> None:
        self._repository = repository
        self._permissions = permission_policy or PermissionPolicy()
        self._audit = audit

    def list_types(
        self,
        actor: User,
        include_inactive: bool = False,
    ) -> list[ReservationType]:
        institution_id = self._scope(actor)
        return list(
            self._repository.list_types(institution_id, include_inactive)
        )

    def get_type(self, actor: User, type_id: str) -> ReservationType:
        institution_id = self._scope(actor)
        reservation_type = self._repository.find_type(type_id)

        if (
            reservation_type is None
            or reservation_type.institution_id != institution_id
        ):
            raise ResourceNotFound("Tipo de reserva não encontrado.")

        return reservation_type

    @audited_mutation
    def create_type(
        self,
        actor: User,
        name: str,
        description: str = "",
    ) -> ReservationType:
        institution_id = self._scope(actor)

        reservation_type = self._repository.add_type(
            ReservationType(
                id=f"rt-{secrets.token_urlsafe(10)}",
                institution_id=institution_id,
                name=" ".join(name.split()),
                description=description.strip(),
            )
        )

        self._record(
            actor,
            AdminAuditAction.RESERVATION_TYPE_CREATED,
            reservation_type.id,
        )
        return reservation_type

    @audited_mutation
    def update_type(
        self,
        actor: User,
        type_id: str,
        name: str,
        description: str = "",
    ) -> ReservationType:
        current = self.get_type(actor, type_id)

        updated = replace(
            current,
            name=" ".join(name.split()),
            description=description.strip(),
        )

        self._repository.save_type(updated)

        if updated != current:
            self._record(
                actor,
                AdminAuditAction.RESERVATION_TYPE_UPDATED,
                updated.id,
            )

        return updated

    @audited_mutation
    def set_type_active(
        self,
        actor: User,
        type_id: str,
        active: bool,
    ) -> ReservationType:
        current = self.get_type(actor, type_id)
        updated = replace(current, active=active)

        self._repository.save_type(updated)

        if current.active != updated.active:
            action = (
                AdminAuditAction.RESERVATION_TYPE_ACTIVATED
                if updated.active
                else AdminAuditAction.RESERVATION_TYPE_DEACTIVATED
            )
            self._record(actor, action, updated.id)

        return updated

    def _record(
        self,
        actor: User,
        action: AdminAuditAction,
        resource_id: str,
    ) -> None:
        if self._audit is not None:
            self._audit.record(actor, action, "reservation_type", resource_id)

    def _scope(self, actor: User) -> str:
        return self._permissions.authorize_listing(
            actor,
            Permission.MANAGE_RESERVATION_TYPES,
        )
