from datetime import datetime
from threading import RLock

from application.ports.admin_audit_repository import AdminAuditRepository
from infrastructure.in_memory_admin_transaction import InMemoryAdminTransaction
from models.domain.entities.admin_audit_event import AdminAuditAction, AdminAuditEvent


class InMemoryAdminAuditRepository(AdminAuditRepository):
    """Temporary process-local append-only administrative history."""

    def __init__(self, *, transaction: InMemoryAdminTransaction | None = None) -> None:
        self._lock = transaction.lock if transaction is not None else RLock()
        self._events: dict[str, AdminAuditEvent] = {}
        if transaction is not None:
            transaction.register(self._events)

    def append(self, event: AdminAuditEvent) -> None:
        with self._lock:
            if event.id in self._events:
                raise ValueError("O identificador do evento de auditoria j\u00e1 existe.")
            self._events[event.id] = event

    def list_for_institution(
        self,
        institution_id: str,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        action: AdminAuditAction | None = None,
        actor_user_id: str | None = None,
        limit: int = 200,
    ) -> tuple[AdminAuditEvent, ...]:
        with self._lock:
            events = (
                event for event in self._events.values()
                if event.institution_id == institution_id
                and (start_at is None or event.occurred_at >= start_at)
                and (end_at is None or event.occurred_at <= end_at)
                and (action is None or event.action is action)
                and (actor_user_id is None or event.actor_user_id == actor_user_id)
            )
            return tuple(sorted(events, key=lambda event: (event.occurred_at, event.id), reverse=True)[:limit])
