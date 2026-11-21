from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import replace
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from application.ports.clock import Clock
from application.ports.institution_repository import InstitutionRepository
from application.ports.reservation_repository import ReservationRepository
from application.ports.space_repository import SpaceRepository
from models.domain.entities.institution import Institution
from models.domain.entities.permission import Permission
from models.domain.entities.profile import Profile
from models.domain.entities.reservation import (
    EDITABLE, REVIEWABLE, Reservation, ReservationDetails, ReservationPeriod, ReservationRequest, ReservationStatus,
)
from models.domain.entities.space import Space
from models.domain.entities.user import User
from models.domain.exceptions import DuplicateResource, ResourceNotFound
from models.domain.policies.permission_policy import PermissionPolicy


def validate_reservation_period(period: ReservationPeriod, institution: Institution, now: datetime) -> None:
    preferences = institution.preferences.reservations
    min_advance = (
        timedelta(hours=preferences.min_advance) if preferences.min_advance_unit == "horas"
        else timedelta(days=preferences.min_advance)
    )
    max_advance = (
        timedelta(days=preferences.max_advance) if preferences.max_advance_unit == "dias"
        else timedelta(weeks=preferences.max_advance)
    )
    if period.start < now + min_advance or period.start > now + max_advance:
        raise ValueError("O início está fora da antecedência de reserva definida pela instituição.")
    zone = ZoneInfo(institution.timezone)
    local_start, local_end = period.start.astimezone(zone), period.end.astimezone(zone)
    if (
        local_start.date() != local_end.date()
        or local_start.time() < time.fromisoformat(preferences.allowed_start)
        or local_end.time() > time.fromisoformat(preferences.allowed_end)
    ):
        raise ValueError("Informe um período dentro do horário institucional, no mesmo dia.")


class ReservationService:
    def __init__(
        self,
        repository: ReservationRepository,
        spaces: SpaceRepository,
        institutions: InstitutionRepository,
        clock: Clock,
        atomic: Callable[[], AbstractContextManager],
        current_actor: Callable[[User], User],
    ) -> None:
        self._repository = repository
        self._spaces = spaces
        self._institutions = institutions
        self._clock = clock
        self._atomic = atomic
        self._current_actor = current_actor
        self._permissions = PermissionPolicy()

    def catalog(self, actor: User, period: ReservationPeriod | None = None) -> tuple[Institution, list[Space]]:
        permission = Permission.REVIEW_RESERVATIONS if actor.profile is Profile.MANAGER else Permission.CREATE_RESERVATION
        institution = self._institution(actor, permission)
        unavailable = (
            self._repository.overlapping_spaces(institution.id, period, approved_only=True) if period else set()
        )
        return institution, [
            room for room in self._spaces.list_spaces(institution.id)
            if room.active and room.status != "bloqueado" and room.id not in unavailable
        ]

    def list_own(self, actor: User) -> list[ReservationDetails]:
        scope = self._permissions.authorize_listing(actor, Permission.VIEW_OWN_RESERVATIONS)
        return self._repository.list(scope, actor.id)

    def list_institution(self, actor: User) -> list[ReservationDetails]:
        scope = self._permissions.authorize_listing(actor, Permission.REVIEW_RESERVATIONS)
        return self._repository.list(scope)

    def create(self, actor: User, request: ReservationRequest) -> ReservationDetails:
        with self._atomic():
            actor = self._current_actor(actor)
            institution = self._institution(actor, Permission.CREATE_RESERVATION)
            request = request.validated()
            now = self._clock.now()
            self._validate(request, institution, now, actor.id)
            status = ReservationStatus.PENDING
            if institution.preferences.reservations.automatic_approval == "no_conflict":
                if not self._overlap(institution.id, request, approved_only=False):
                    status = ReservationStatus.APPROVED
            return self._repository.add(Reservation(
                "", institution.id, actor.id, request, status, now,
                reviewed_at=now if status is ReservationStatus.APPROVED else None,
            ))

    def edit(self, actor: User, reservation_id: str, request: ReservationRequest) -> ReservationDetails:
        with self._atomic():
            actor = self._current_actor(actor)
            manager = actor.profile is Profile.MANAGER
            permission = Permission.REVIEW_RESERVATIONS if manager else Permission.CREATE_RESERVATION
            institution = self._institution(actor, permission)
            details = self._find(institution.id, reservation_id, None if manager else actor.id)
            current = details.reservation
            now = self._clock.now()
            if current.status not in EDITABLE or current.request.period.start <= now:
                raise DuplicateResource("Esta reserva não permite alterações.")
            request = request.validated()
            if request == current.request:
                return details
            self._validate(request, institution, now, current.requester_id, exclude_id=current.id)
            return self._repository.save(replace(
                current, request=request, status=ReservationStatus.IN_REVIEW,
                reviewed_by=None, reviewed_at=None, decision_reason=None,
            ))

    def cancel(self, actor: User, reservation_id: str) -> ReservationDetails:
        with self._atomic():
            actor = self._current_actor(actor)
            scope = self._permissions.authorize_listing(actor, Permission.CANCEL_OWN_RESERVATION)
            current = self._find(scope, reservation_id, actor.id).reservation
            if current.status not in EDITABLE or current.request.period.start <= self._clock.now():
                raise DuplicateResource("Esta reserva não pode ser cancelada.")
            return self._repository.save(replace(current, status=ReservationStatus.CANCELLED))

    def review(
        self, actor: User, reservation_id: str, status: ReservationStatus, reason: str | None,
    ) -> ReservationDetails:
        with self._atomic():
            actor = self._current_actor(actor)
            institution = self._institution(actor, Permission.REVIEW_RESERVATIONS)
            current = self._find(institution.id, reservation_id).reservation
            now = self._clock.now()
            if current.status not in REVIEWABLE or current.status is status:
                raise DuplicateResource("A transição solicitada não está disponível para esta reserva.")
            reason = (reason or "").strip()
            if status is ReservationStatus.APPROVED:
                if current.request.period.start <= now:
                    raise DuplicateResource("O período da reserva já começou.")
                self._validate_room(current.request, institution.id, exclude_id=current.id)
            elif status is ReservationStatus.REJECTED:
                if not reason:
                    raise ValueError("Informe o motivo da rejeição.")
            elif status is not ReservationStatus.IN_REVIEW:
                raise ValueError("Decisão de reserva inválida.")
            return self._repository.save(replace(
                current, status=status, reviewed_by=actor.id, reviewed_at=now, decision_reason=reason or None,
            ))

    def _institution(self, actor: User, permission: Permission) -> Institution:
        scope = self._permissions.authorize_listing(actor, permission)
        institution = self._institutions.find_by_id(scope)
        if institution is None:
            raise ResourceNotFound("Instituição não encontrada.")
        return institution

    def _find(self, scope: str, reservation_id: str, requester_id: str | None = None) -> ReservationDetails:
        result = self._repository.find(scope, reservation_id, requester_id)
        if result is None:
            raise ResourceNotFound("Reserva não encontrada.")
        return result

    def _validate(
        self, request: ReservationRequest, institution: Institution, now: datetime,
        requester_id: str, exclude_id: str | None = None,
    ) -> None:
        validate_reservation_period(request.period, institution, now)
        if institution.preferences.reservations.justification_required and not request.justification:
            raise ValueError("Informe a justificativa da solicitação.")
        self._validate_room(request, institution.id, exclude_id)
        if self._overlap(institution.id, request, approved_only=False, exclude_id=exclude_id, requester_id=requester_id):
            raise DuplicateResource("O solicitante já tem uma reserva para esta sala no período informado.")

    def _validate_room(self, request: ReservationRequest, scope: str, exclude_id: str | None) -> None:
        room = self._spaces.find_space(request.space_id)
        if room is None or room.institution_id != scope:
            raise ResourceNotFound("Sala não encontrada.")
        if not room.active or room.status == "bloqueado":
            raise DuplicateResource("A sala está bloqueada ou inativa.")
        if request.participants > room.capacity:
            raise ValueError("A quantidade de participantes excede a capacidade da sala.")
        if self._overlap(scope, request, approved_only=True, exclude_id=exclude_id):
            raise DuplicateResource("Já existe uma reserva aprovada para esta sala no período informado.")

    def _overlap(
        self, scope: str, request: ReservationRequest, *, approved_only: bool, exclude_id: str | None = None,
        requester_id: str | None = None,
    ) -> bool:
        return bool(self._repository.overlapping_spaces(
            scope, request.period, approved_only=approved_only, space_id=request.space_id, exclude_id=exclude_id,
            requester_id=requester_id,
        ))
