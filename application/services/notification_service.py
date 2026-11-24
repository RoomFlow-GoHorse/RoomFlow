from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime

from application.ports.clock import Clock
from application.ports.institution_repository import InstitutionRepository
from application.ports.reservation_repository import ReservationRepository
from application.ports.notification_repository import NotificationRepository
from application.ports.user_repository import UserRepository
from models.domain.entities.institution import Institution
from models.domain.entities.notification import Notification
from models.domain.entities.permission import Permission
from models.domain.entities.reservation import Reservation, ReservationHistoryAction, ReservationHistoryEvent, ReservationStatus
from models.domain.entities.user import User
from models.domain.exceptions import ResourceNotFound
from models.domain.policies.permission_policy import PermissionPolicy


class NotificationService:
    def __init__(
        self, repository: NotificationRepository, institutions: InstitutionRepository, users: UserRepository,
        clock: Clock, snapshot: Callable[[], AbstractContextManager], reservations: ReservationRepository | None = None,
    ) -> None:
        self._repository = repository
        self._institutions = institutions
        self._users = users
        self._clock = clock
        self._snapshot = snapshot
        self._permissions = PermissionPolicy()
        self._reservations = reservations

    def inbox(
        self, actor: User, *, unread_only: bool, category: str | None, limit: int, offset: int,
    ) -> tuple[list[Notification], int, int, str]:
        scope = self._scope(actor)
        with self._snapshot():
            institution = self._institution(scope)
            items, total = self._repository.inbox(
                scope, actor.id, unread_only=unread_only, category=category, limit=limit, offset=offset,
            )
            return items, total, self._repository.unread_count(scope, actor.id), institution.timezone

    def unread_count(self, actor: User) -> int:
        return self._repository.unread_count(self._scope(actor), actor.id)

    def mark_read(self, actor: User, notification_id: str) -> datetime:
        read_at = self._repository.mark_read(self._scope(actor), actor.id, notification_id, self._clock.now())
        if read_at is None:
            raise ResourceNotFound("Notificação não encontrada.")
        return read_at

    def mark_all_read(self, actor: User) -> int:
        return self._repository.mark_all_read(self._scope(actor), actor.id, self._clock.now())

    def record_reservation_event(
        self, current: Reservation, event: ReservationHistoryEvent, previous: Reservation | None = None,
    ) -> None:
        """Persist one event and its audience inside the reservation transaction."""
        institution_id = current.institution_id
        preferences = self._institution(institution_id).preferences.notifications
        action = event.action
        booking = f'“{current.request.title}” (#{current.id})'

        if action is ReservationHistoryAction.CREATE:
            title, message = "Nova solicitação de reserva", f"Foi registrada uma nova solicitação para {booking}."
            reviewer, requester, category = True, False, "reserva"
        elif action in (ReservationHistoryAction.REVIEW, ReservationHistoryAction.AUTO_APPROVAL):
            if event.status is ReservationStatus.APPROVED and preferences.reservation_approved:
                title, message = "Reserva aprovada", f"A reserva {booking} foi aprovada."
            elif event.status is ReservationStatus.REJECTED and preferences.reservation_rejected:
                title, message = "Reserva rejeitada", f"A reserva {booking} foi rejeitada."
                if event.reason:
                    message = f"{message} Motivo informado: {event.reason}"
            else:
                return
            reviewer, requester, category = False, True, "reserva"
        elif action is ReservationHistoryAction.CANCEL and preferences.reservation_cancelled:
            title, message = "Reserva cancelada", f"A reserva {booking} foi cancelada."
            reviewer, requester, category = True, True, "reserva"
        elif action is ReservationHistoryAction.EDIT and preferences.space_changed and previous is not None:
            changed = self._changed_fields(previous, current)
            if not changed:
                return
            title, message = "Reserva alterada", f"A reserva {booking} teve alteração de {', '.join(changed)}."
            reviewer, requester, category = True, current.requester_id != event.actor_id, "alteracao"
        else:
            return

        recipients = set()
        if reviewer:
            recipients.update(
                user.id for account in self._users.list_by_institution(institution_id)
                if (user := account.user).is_active and user.id != event.actor_id
                and Permission.REVIEW_RESERVATIONS in self._permissions.effective_permissions(user.profile)
            )
        if requester:
            account = self._users.find_by_id(current.requester_id, institution_id)
            if account is not None and account.user.is_active:
                recipients.add(account.user.id)
        if self._reservations is not None:
            recipients.update(
                participant.user_id for participant in self._reservations.participants(institution_id, current.id)
                if participant.user_id != event.actor_id
            )
        if recipients:
            self._repository.add(institution_id, Notification(
                title, message, category, event.occurred_at, reservation_id=current.id,
            ), frozenset(recipients))

    @staticmethod
    def _changed_fields(previous: Reservation, current: Reservation) -> list[str]:
        return [
            label for field, label in (
                ("space_id", "sala"), ("period", "horário"), ("participants", "número de participantes"),
                ("title", "título"), ("activity_type", "tipo de atividade"),
            )
            if getattr(previous.request, field) != getattr(current.request, field)
        ]

    def _scope(self, actor: User) -> str:
        return self._permissions.authorize_listing(actor, Permission.VIEW_NOTIFICATIONS)

    def _institution(self, institution_id: str) -> Institution:
        institution = self._institutions.find_by_id(institution_id)
        if institution is None:
            raise ResourceNotFound("Instituição não encontrada.")
        return institution
