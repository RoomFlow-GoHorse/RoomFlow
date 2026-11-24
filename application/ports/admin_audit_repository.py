from datetime import datetime
from typing import Protocol, Sequence

from models.domain.entities.admin_audit_event import AdminAuditAction, AdminAuditEvent


class AdminAuditRepository(Protocol):
    def append(self, event: AdminAuditEvent) -> None: ...

    def list_for_institution(
        self,
        institution_id: str,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        action: AdminAuditAction | None = None,
        actor_user_id: str | None = None,
        limit: int = 200,
    ) -> Sequence[AdminAuditEvent]: ...
