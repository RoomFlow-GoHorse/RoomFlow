from controllers.operation_presenters import room_response as _room
from dataclasses import asdict
from datetime import date, time

from fastapi import APIRouter, Depends, Query, Request, Response

from application.services.manager_operations_service import ManagerOperationsService
from controllers.http.dependencies import get_current_user
from controllers.http.reservations import reservation_response, run_reservation_action
from models.domain.entities.reservation import ReservationStatus
from models.domain.entities.space import Space
from models.domain.entities.user import User


router = APIRouter(prefix="/manager/operations", tags=["manager operations"])


def get_service(request: Request) -> ManagerOperationsService:
    return request.app.state.manager_operations_service


@router.get("/context")
def context(
    response: Response,
    actor: User = Depends(get_current_user),
    service: ManagerOperationsService = Depends(get_service),
):
    result = run_reservation_action(lambda: service.context(actor))
    response.headers["Cache-Control"] = "private, no-store"
    return {"data": {
        "timezone": result.timezone, "today": result.today,
        "opens_at": result.opens_at, "closes_at": result.closes_at,
        "buildings": [{"id": item.id, "name": item.name} for item in result.buildings],
        "spaces": [_room(room) for room in result.spaces],
    }}


@router.get("")
def report(
    response: Response,
    start_date: date | None = None,
    end_date: date | None = None,
    start_time: time | None = None,
    end_time: time | None = None,
    building_id: str | None = Query(default=None, min_length=1, max_length=64),
    space_id: str | None = Query(default=None, min_length=1, max_length=19),
    status: ReservationStatus | None = None,
    actor: User = Depends(get_current_user),
    service: ManagerOperationsService = Depends(get_service),
):
    """Counts all statuses inside the selected period. Status only filters the timeline."""
    result = run_reservation_action(lambda: service.report(
        actor, start_date, end_date, building_id, space_id, status, start_time, end_time,
    ))
    response.headers["Cache-Control"] = "private, no-store"
    return {"data": {
        "timezone": result.timezone, "start_date": result.start_date, "end_date": result.end_date,
        "opens_at": result.opens_at, "closes_at": result.closes_at,
        "metrics": asdict(result.metrics),
        "occupancy_rate": result.occupancy_rate,
        "space_counts": result.space_counts,
        "spaces": [
            {**_room(row.room), "status": row.status, "occupancy_rate": row.rate,
             "usable_seconds": row.usable_seconds, "occupied_seconds": row.occupied_seconds,
             "blocked_seconds": row.blocked_seconds}
            for row in result.spaces
        ],
        "reservations": [reservation_response(row) for row in result.reservations],
    }}
