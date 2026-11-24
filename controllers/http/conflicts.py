from controllers.operation_presenters import conflict_response as _response
from controllers.operation_payloads import ResolutionPayload
from fastapi import APIRouter, Depends, Query, Request

from application.services.conflict_service import ConflictService
from controllers.http.dependencies import get_current_user
from controllers.http.reservations import reservation_response, run_reservation_action
from models.domain.entities.reservation_conflict import ConflictAction, ConflictDetails, ConflictStatus
from models.domain.entities.user import User


router = APIRouter(prefix="/conflicts", tags=["conflicts"])


def get_service(request: Request) -> ConflictService:
    return request.app.state.conflict_service


@router.get("")
def list_conflicts(
    status: ConflictStatus | None = None,
    query: str = Query(default="", max_length=120),
    actor: User = Depends(get_current_user),
    service: ConflictService = Depends(get_service),
):
    timezone, items = run_reservation_action(lambda: service.list_conflicts(actor, status, query))
    return {"data": {"timezone": timezone, "items": [_response(item) for item in items]}}


@router.post("/detect")
def detect(actor: User = Depends(get_current_user), service: ConflictService = Depends(get_service)):
    return {"data": {"updated": run_reservation_action(lambda: service.detect(actor))}}


@router.get("/{conflict_id}")
def detail(
    conflict_id: str, actor: User = Depends(get_current_user), service: ConflictService = Depends(get_service),
):
    item, actions = run_reservation_action(lambda: service.detail(actor, conflict_id))
    return {"data": {**_response(item), "available_actions": actions}}


@router.get("/{conflict_id}/alternatives")
def alternatives(
    conflict_id: str, actor: User = Depends(get_current_user), service: ConflictService = Depends(get_service),
):
    result = run_reservation_action(lambda: service.alternatives(actor, conflict_id))
    return {"data": {
        reservation_id: [
            {"id": room.id, "name": room.name, "location": room.location, "capacity": room.capacity}
            for room in rooms
        ]
        for reservation_id, rooms in result.items()
    }}


@router.post("/{conflict_id}/resolve")
def resolve(
    conflict_id: str, payload: ResolutionPayload,
    actor: User = Depends(get_current_user), service: ConflictService = Depends(get_service),
):
    item, actions = run_reservation_action(lambda: service.resolve(
        actor, conflict_id, payload.action, payload.reason, payload.reservation_id, payload.space_id,
    ))
    return {"data": {**_response(item), "available_actions": actions}}
