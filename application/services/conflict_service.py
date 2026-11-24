from collections.abc import Callable
from contextlib import AbstractContextManager

from application.ports.clock import Clock
from application.ports.conflict_repository import ConflictRepository
from application.ports.institution_repository import InstitutionRepository
from application.ports.reservation_repository import ReservationRepository
from application.services.reservation_service import ReservationService
from models.domain.entities.institution import Institution
from models.domain.entities.permission import Permission
from models.domain.entities.reservation import ReservationStatus
from models.domain.entities.reservation_conflict import ConflictAction, ConflictDetails, ConflictStatus
from models.domain.entities.space import Space
from models.domain.entities.user import User
from models.domain.exceptions import DuplicateResource, ResourceNotFound
from models.domain.policies.permission_policy import PermissionPolicy


class ConflictService:
    def __init__(
        self, repository: ConflictRepository, reservations: ReservationRepository,
        reservation_service: ReservationService, institutions: InstitutionRepository, clock: Clock,
        atomic: Callable[[], AbstractContextManager], current_actor: Callable[[User], User],
    ) -> None:
        self._repository = repository
        self._reservations = reservations
        self._reservation_service = reservation_service
        self._institutions = institutions
        self._clock = clock
        self._atomic = atomic
        self._current_actor = current_actor
        self._permissions = PermissionPolicy()

    def list_conflicts(
        self, actor: User, status: ConflictStatus | None = None, query: str = "",
    ) -> tuple[str, list[ConflictDetails]]:
        institution = self._institution(actor)
        conflicts = self._repository.list(institution.id, status)
        ids = {item for conflict in conflicts for item in (conflict.reservation_a_id, conflict.reservation_b_id)}
        reservations = self._reservations.find_many(institution.id, ids)
        details = [
            ConflictDetails(conflict, reservations[conflict.reservation_a_id], reservations[conflict.reservation_b_id])
            for conflict in conflicts
            if conflict.reservation_a_id in reservations and conflict.reservation_b_id in reservations
        ]
        search = query.strip().casefold()
        return institution.timezone, [
            item for item in details if search in " ".join((
                item.conflict.id, item.reservation_a.space_name, item.reservation_b.space_name,
                item.reservation_a.requester_name, item.reservation_b.requester_name,
            )).casefold()
        ]

    def detail(self, actor: User, conflict_id: str) -> tuple[ConflictDetails, tuple[ConflictAction, ...]]:
        item = self._find(self._scope(actor), conflict_id)
        return item, item.actions(self._clock.now())

    def alternatives(self, actor: User, conflict_id: str) -> dict[str, list[Space]]:
        institution = self._institution(actor)
        item = self._find(institution.id, conflict_id)
        now = self._clock.now()
        if ConflictAction.MOVE not in item.actions(now) or not institution.preferences.conflicts.suggest_alternatives:
            return {}
        reservations = (item.reservation_a.reservation, item.reservation_b.reservation)
        return {reservation.id: self._reservation_service.alternative_rooms(reservation, now)
                for reservation in reservations}

    def detect(self, actor: User) -> int:
        with self._atomic():
            actor = self._current_actor(actor)
            return self._repository.synchronize(self._scope(actor), self._clock.now(), actor.id)

    def resolve(
        self, actor: User, conflict_id: str, action: ConflictAction, reason: str,
        reservation_id: str | None = None, space_id: str | None = None,
    ) -> tuple[ConflictDetails, tuple[ConflictAction, ...]]:
        reason = reason.strip()
        if not 1 <= len(reason) <= 600:
            raise ValueError("Informe uma justificativa de até 600 caracteres.")
        with self._atomic():
            actor = self._current_actor(actor)
            scope = self._scope(actor)
            item = self._find(scope, conflict_id)
            now = self._clock.now()
            if action not in item.actions(now):
                raise DuplicateResource("A decisão não está disponível no estado atual das reservas.")
            a, b = item.reservation_a.reservation, item.reservation_b.reservation

            if action is ConflictAction.MOVE:
                if reservation_id not in (a.id, b.id) or space_id is None:
                    raise ValueError("Selecione uma das reservas do conflito e a sala alternativa.")
                decision = f"Reserva #{reservation_id} movida para a sala #{space_id}. {reason}"
                self._repository.resolve(item.conflict, decision, actor.id, now)
                self._reservation_service.move_for_conflict(actor, reservation_id, space_id, reason)
            else:
                if reservation_id is not None or space_id is not None:
                    raise ValueError("Informe sala e reserva apenas ao mover uma reserva.")
                winner, other = (a, b) if action is ConflictAction.KEEP_A else (b, a)
                self._repository.resolve(item.conflict, f"Reserva #{winner.id} mantida. {reason}", actor.id, now)
                self._reservation_service.review(actor, other.id, ReservationStatus.REJECTED, reason)
                if winner.status is not ReservationStatus.APPROVED:
                    self._reservation_service.review(actor, winner.id, ReservationStatus.APPROVED, reason)

            return self._find(scope, conflict_id), ()

    def _scope(self, actor: User) -> str:
        return self._permissions.authorize_listing(actor, Permission.RESOLVE_CONFLICTS)

    def _institution(self, actor: User) -> Institution:
        institution = self._institutions.find_by_id(self._scope(actor))
        if institution is None:
            raise ResourceNotFound("Instituição não encontrada.")
        return institution

    def _find(self, scope: str, conflict_id: str) -> ConflictDetails:
        conflict = self._repository.find(scope, conflict_id)
        if conflict is None:
            raise ResourceNotFound("Conflito não encontrado.")
        reservations = self._reservations.find_many(scope, {conflict.reservation_a_id, conflict.reservation_b_id})
        if len(reservations) != 2:
            raise ResourceNotFound("Reservas do conflito não encontradas.")
        return ConflictDetails(conflict, reservations[conflict.reservation_a_id], reservations[conflict.reservation_b_id])
