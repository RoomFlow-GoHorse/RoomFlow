from collections import defaultdict
from collections.abc import Callable, Iterable
from contextlib import AbstractContextManager
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from application.ports.clock import Clock
from application.ports.institution_repository import InstitutionRepository
from application.ports.reservation_dashboard_query import ReservationDashboardQuery
from application.ports.room_block_query import RoomBlockQuery
from application.ports.space_repository import SpaceRepository
from application.read_models.manager_operations import ManagerOperations, ManagerOperationsContext, RoomOccupancy
from application.services.reservation_service import ReservationService
from models.domain.entities.permission import Permission
from models.domain.entities.reservation import ReservationPeriod, ReservationStatus
from models.domain.entities.space import Space
from models.domain.entities.user import User
from models.domain.exceptions import ResourceNotFound
from models.domain.policies.permission_policy import PermissionPolicy


def _merged(periods: Iterable[ReservationPeriod]) -> list[ReservationPeriod]:
    merged: list[ReservationPeriod] = []
    for period in sorted(periods, key=lambda interval: interval.start):
        if merged and period.start <= merged[-1].end:
            previous = merged.pop()
            period = ReservationPeriod(previous.start, max(previous.end, period.end))
        merged.append(period)
    return merged


def _open_periods(
    windows: Iterable[ReservationPeriod], blocks: list[ReservationPeriod],
) -> Iterable[ReservationPeriod]:
    for window in windows:
        cursor = window.start
        for block in blocks:
            if block.start >= window.end:
                break
            if block.end <= cursor:
                continue
            if cursor < block.start:
                yield ReservationPeriod(cursor, block.start)
            cursor = max(cursor, block.end)
            if cursor >= window.end:
                break
        if cursor < window.end:
            yield ReservationPeriod(cursor, window.end)


def _duration(periods: Iterable[ReservationPeriod]) -> float:
    return sum((period.end - period.start).total_seconds() for period in periods)


def room_occupancy(
    room: Space, windows: tuple[ReservationPeriod, ...], approvals: Iterable[ReservationPeriod],
    blocks: Iterable[ReservationPeriod],
) -> RoomOccupancy:
    if not room.active:
        return RoomOccupancy(room, "inativo", 0, 0, 0)
    operating = tuple(
        ReservationPeriod(max(window.start, room.created_at), window.end) if room.created_at else window
        for window in windows if room.created_at is None or room.created_at < window.end
    )
    if not operating:
        return RoomOccupancy(room, "indisponivel", 0, 0, 0)
    if room.status == "bloqueado" and room.block_reason is None:
        # Legacy room flags have no dates to restrict the block to.
        return RoomOccupancy(room, "bloqueado", 0, 0, _duration(operating))
    open_periods = tuple(_open_periods(operating, _merged(blocks)))
    usable = _duration(open_periods)
    blocked = max(0, _duration(operating) - usable)
    occupied = sum(
        (min(window.end, booking.end) - max(window.start, booking.start)).total_seconds()
        for booking in _merged(approvals)
        for window in open_periods
        if booking.start < window.end and booking.end > window.start
    )
    status = "bloqueado" if blocked else "ocupado" if occupied else "disponivel"
    return RoomOccupancy(room, status, usable, occupied, blocked)


class ManagerOperationsService:
    def __init__(
        self, institutions: InstitutionRepository, spaces: SpaceRepository,
        reservations: ReservationService, dashboard_query: ReservationDashboardQuery, blocks: RoomBlockQuery,
        clock: Clock, snapshot: Callable[[], AbstractContextManager],
    ) -> None:
        self._institutions = institutions
        self._spaces = spaces
        self._reservations = reservations
        self._dashboard = dashboard_query
        self._blocks = blocks
        self._clock = clock
        self._snapshot = snapshot
        self._permissions = PermissionPolicy()

    def context(self, actor: User) -> ManagerOperationsContext:
        with self._snapshot():
            return self._context(self._scope(actor))

    def report(
        self, actor: User, start_date: date | None, end_date: date | None,
        building_id: str | None, space_id: str | None, status: ReservationStatus | None,
        start_time: time | None = None, end_time: time | None = None,
    ) -> ManagerOperations:
        with self._snapshot():
            institution_id = self._scope(actor)
            context = self._context(institution_id)
            start = start_date or context.today
            end = end_date or start
            opens, closes, period, windows = self._periods(context, start, end, start_time, end_time)
            if building_id is not None and not any(building.id == building_id for building in context.buildings):
                raise ResourceNotFound("Prédio não encontrado.")
            rooms = tuple(
                room for room in context.spaces
                if (building_id is None or room.building_id == building_id)
                and (space_id is None or room.id == space_id)
            )
            if space_id is not None and not rooms:
                raise ResourceNotFound("Nenhuma sala encontrada para os filtros selecionados.")
            ids = frozenset(room.id for room in rooms)
            reservations = self._reservations.list_for_operations(actor, period, ids)
            metrics = self._dashboard.get_metrics(institution_id, period.start, period.end, space_ids=ids)
            blocks = self._blocks.block_periods(institution_id, period) if rooms else {}
            approved = defaultdict(list)
            for item in reservations:
                booking = item.reservation
                if booking.status is ReservationStatus.APPROVED:
                    approved[booking.request.space_id].append(booking.request.period)
            return ManagerOperations(
                context.timezone, start, end, opens, closes, metrics,
                tuple(room_occupancy(room, windows, approved[room.id], blocks.get(room.id, ())) for room in rooms),
                tuple(item for item in reservations if status is None or item.reservation.status is status),
            )

    def _scope(self, actor: User) -> str:
        return self._permissions.authorize_listing(actor, Permission.VIEW_MANAGER_DASHBOARD)

    def _context(self, institution_id: str) -> ManagerOperationsContext:
        institution = self._institutions.find_by_id(institution_id)
        if institution is None:
            raise ResourceNotFound("Instituição não encontrada.")
        preferences = institution.preferences.reservations
        return ManagerOperationsContext(
            institution.timezone, self._clock.now().astimezone(ZoneInfo(institution.timezone)).date(),
            time.fromisoformat(preferences.allowed_start), time.fromisoformat(preferences.allowed_end),
            tuple(self._spaces.list_spaces(institution_id, include_inactive=True)),
            tuple(self._spaces.list_buildings(institution_id, include_inactive=True)),
        )

    @staticmethod
    def _periods(context, start, end, start_time, end_time):
        days = (end - start).days + 1
        if not 1 <= days <= 366 or end == date.max:
            raise ValueError("Informe um período válido de até 366 dias.")
        if start_time is not None or end_time is not None:
            if (
                days != 1 or start_time is None or end_time is None
                or start_time.tzinfo is not None or end_time.tzinfo is not None
                or not context.opens_at <= start_time < end_time <= context.closes_at
            ):
                raise ValueError("Informe início e fim dentro do horário institucional para um único dia.")
        opens, closes = start_time or context.opens_at, end_time or context.closes_at
        zone = ZoneInfo(context.timezone)
        windows = tuple(
            ReservationPeriod(datetime.combine(day, opens, zone), datetime.combine(day, closes, zone))
            for day in (start + timedelta(days=index) for index in range(days))
        )
        period = windows[0] if start_time is not None else ReservationPeriod(
            datetime.combine(start, time.min, zone), datetime.combine(end + timedelta(days=1), time.min, zone),
        )
        return opens, closes, period, windows
