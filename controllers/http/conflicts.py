from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from application.services.conflict_service import ConflictService
from controllers.http.dependencies import get_current_user
from controllers.http.reservations import reservation_response, run_reservation_action
from models.domain.entities.reservation_conflict import ConflictAction, ConflictDetails, ConflictStatus
from models.domain.entities.user import User


router = APIRouter(prefix="/conflicts", tags=["conflicts"])


class ResolutionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ConflictAction
    reason: str = Field(min_length=1, max_length=600)
    reservation_id: str | None = Field(default=None, min_length=1, max_length=19)
    space_id: str | None = Field(default=None, min_length=1, max_length=19)


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


def _response(item: ConflictDetails) -> dict:
    conflict = item.conflict
    return {
        "id": conflict.id, "status": conflict.status, "severity": conflict.severity,
        "reason": conflict.reason, "created_at": conflict.created_at, "decision": conflict.decision,
        "resolved_at": conflict.resolved_at, "resolved_by": conflict.resolved_by,
        "resolver_name": conflict.resolver_name,
        "reservations": [reservation_response(item.reservation_a), reservation_response(item.reservation_b)],
    }
