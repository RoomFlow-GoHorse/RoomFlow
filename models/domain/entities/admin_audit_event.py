from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AdminAuditAction(str, Enum):
    USER_CREATED = "user.created"
    USER_PROFILE_CHANGED = "user.profile_changed"
    USER_ACTIVATED = "user.activated"
    USER_DEACTIVATED = "user.deactivated"
    USER_ACCOUNT_UPDATED = "user.account_updated"
    INSTITUTION_CREATED = "institution.created"
    INSTITUTION_SETTINGS_UPDATED = "institution.settings_updated"
    INVITATION_CODE_GENERATED = "institution.invitation_code.generated"
    INVITATION_CODE_REPLACED = "institution.invitation_code.replaced"
    INVITATION_CODE_REVOKED = "institution.invitation_code.revoked"
    ENROLLMENT_CREATED = "enrollment.created"
    ENROLLMENT_DEACTIVATED = "enrollment.deactivated"
    ENROLLMENT_IMPORTED = "enrollment.imported"
    BUILDING_CREATED = "building.created"
    BUILDING_UPDATED = "building.updated"
    BUILDING_ACTIVATED = "building.activated"
    BUILDING_DEACTIVATED = "building.deactivated"
    FLOOR_CREATED = "floor.created"
    FLOOR_UPDATED = "floor.updated"
    FLOOR_ACTIVATED = "floor.activated"
    FLOOR_DEACTIVATED = "floor.deactivated"
    SPACE_CREATED = "space.created"
    SPACE_UPDATED = "space.updated"
    SPACE_BLOCKED = "space.blocked"
    SPACE_UNBLOCKED = "space.unblocked"
    SPACE_ACTIVATED = "space.activated"
    SPACE_DEACTIVATED = "space.deactivated"
    SPACE_RESOURCES_UPDATED = "space.resources_updated"
    RESOURCE_CREATED = "resource.created"
    RESOURCE_UPDATED = "resource.updated"
    RESOURCE_ACTIVATED = "resource.activated"
    RESOURCE_DEACTIVATED = "resource.deactivated"
    FLOOR_PLAN_UPLOADED = "floor_plan.uploaded"
    FLOOR_PLAN_REPLACED = "floor_plan.replaced"
    FLOOR_PLAN_REMOVED = "floor_plan.removed"
    FLOOR_PLAN_POSITION_SET = "floor_plan.position_set"
    FLOOR_PLAN_POSITION_REMOVED = "floor_plan.position_removed"


@dataclass(frozen=True, slots=True)
class AdminAuditEvent:
    id: str
    institution_id: str
    actor_user_id: str
    actor_name: str
    action: AdminAuditAction
    resource_type: str
    resource_id: str
    occurred_at: datetime

    def __post_init__(self) -> None:
        if not all((self.id.strip(), self.institution_id.strip(), self.actor_user_id.strip(), self.resource_type.strip(), self.resource_id.strip())):
            raise ValueError("O evento de auditoria precisa identificar ator, institui\u00e7\u00e3o e recurso.")
        if not self.actor_name.strip():
            raise ValueError("O evento de auditoria precisa identificar o respons\u00e1vel.")
        if not isinstance(self.action, AdminAuditAction):
            object.__setattr__(self, "action", AdminAuditAction(self.action))
