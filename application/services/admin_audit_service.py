import secrets
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from datetime import datetime, timezone
from functools import wraps
from typing import Concatenate, ParamSpec, Protocol, TypeVar

from application.ports.admin_audit_repository import AdminAuditRepository
from application.ports.clock import Clock
from application.ports.user_repository import UserRepository
from models.domain.entities.admin_audit_event import AdminAuditAction, AdminAuditEvent
from models.domain.entities.permission import Permission
from models.domain.entities.user import User
from models.domain.exceptions import PermissionDenied
from models.domain.policies.permission_policy import PermissionPolicy


class AuditedService(Protocol):
    @property
    def _audit(self) -> "AdminAuditService | None": ...


P = ParamSpec("P")
R = TypeVar("R")
S = TypeVar("S", bound=AuditedService)


def audited_mutation(
    method: Callable[Concatenate[S, User, P], R],
) -> Callable[Concatenate[S, User, P], R]:
    @wraps(method)
    def wrapped(self: S, /, actor: User, *args: P.args, **kwargs: P.kwargs) -> R:
        if self._audit is None:
            return method(self, actor, *args, **kwargs)
        with self._audit.atomic():
            return method(self, self._audit.current_actor(actor), *args, **kwargs)

    return wrapped


class AdminAuditService:
    """Records successful administrative mutations and reads scoped history."""

    def __init__(
        self,
        repository: AdminAuditRepository,
        clock: Clock,
        permission_policy: PermissionPolicy | None = None,
        atomic: Callable[[], AbstractContextManager] = nullcontext,
        users: UserRepository | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._permissions = permission_policy or PermissionPolicy()
        self.atomic = atomic
        self._users = users

    def current_actor(self, actor: User) -> User:
        if self._users is None:
            return actor
        account = self._users.find_by_id(actor.id)
        if account is None or not account.user.is_active:
            raise PermissionDenied("A conta do responsável não está ativa.")
        return account.user

    def record(
        self,
        actor: User,
        action: AdminAuditAction,
        resource_type: str,
        resource_id: str,
    ) -> AdminAuditEvent:
        institution_id = actor.institution_id
        if institution_id is None:
            raise ValueError("O evento exige v\u00ednculo institucional do respons\u00e1vel.")
        event = AdminAuditEvent(
            id=f"audit-{secrets.token_urlsafe(12)}",
            institution_id=institution_id,
            actor_user_id=actor.id,
            actor_name=actor.name,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            occurred_at=self._clock.now(),
        )
        self._repository.append(event)
        return event

    def list_events(
        self,
        actor: User,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        action: AdminAuditAction | None = None,
        actor_user_id: str | None = None,
        limit: int = 200,
    ) -> list[AdminAuditEvent]:
        institution_id = self._permissions.authorize_listing(self.current_actor(actor), Permission.VIEW_ADMIN_AUDIT)
        if limit < 1 or limit > 500:
            raise ValueError("O limite deve estar entre 1 e 500 eventos.")
        for boundary in (start_at, end_at):
            if boundary is not None and boundary.utcoffset() is None:
                raise ValueError("Informe o fuso horário nas datas do histórico.")
        start_at = start_at.astimezone(timezone.utc) if start_at else None
        end_at = end_at.astimezone(timezone.utc) if end_at else None
        if start_at and end_at and start_at > end_at:
            raise ValueError("A data inicial deve ser anterior ou igual à data final.")
        return list(self._repository.list_for_institution(
            institution_id,
            start_at=start_at,
            end_at=end_at,
            action=action,
            actor_user_id=actor_user_id,
            limit=limit,
        ))
