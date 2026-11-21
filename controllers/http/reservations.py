from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from application.services.reservation_service import ReservationService
from controllers.http.dependencies import get_current_user
from models.domain.entities.reservation import (
    ReservationDetails, ReservationPeriod, ReservationRequest, ReservationStatus, review_decisions,
)
from models.domain.entities.user import User
from models.domain.exceptions import DomainAuthorizationError, DuplicateResource, ResourceNotFound


router = APIRouter(prefix="/reservations", tags=["reservations"])


class ReservationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    space_id: str = Field(min_length=1, max_length=19)
    title: str = Field(min_length=1, max_length=200)
    activity_type: str = Field(min_length=1, max_length=60)
    start: datetime
    end: datetime
    participants: int = Field(strict=True, ge=1, le=10000)
    justification: str | None = Field(default=None, max_length=600)

    def to_request(self) -> ReservationRequest:
        return ReservationRequest(
            self.space_id, self.title, self.activity_type, ReservationPeriod(self.start, self.end),
            self.participants, self.justification,
        )


class DecisionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ReservationStatus
    reason: str | None = Field(default=None, max_length=600)


def get_service(request: Request) -> ReservationService:
    return request.app.state.reservation_service


@router.get("/spaces")
def list_spaces(
    start: datetime | None = None,
    end: datetime | None = None,
    actor: User = Depends(get_current_user),
    service: ReservationService = Depends(get_service),
):
    if (start is None) != (end is None):
        raise HTTPException(422, "Informe início e fim juntos.")
    institution, spaces = run_reservation_action(lambda: service.catalog(
        actor, ReservationPeriod(start, end) if start is not None and end is not None else None,
    ))
    return {"data": {
        "timezone": institution.timezone,
        "justification_required": institution.preferences.reservations.justification_required,
        "spaces": [
            {"id": item.id, "name": item.name, "type": item.type, "building": item.building,
             "building_id": item.building_id, "location": item.location, "capacity": item.capacity,
             "resources": list(item.resources)}
            for item in spaces
        ],
    }}


@router.post("", status_code=201)
def create(
    payload: ReservationPayload,
    actor: User = Depends(get_current_user),
    service: ReservationService = Depends(get_service),
):
    return {"data": reservation_response(run_reservation_action(lambda: service.create(actor, payload.to_request())))}


@router.get("/mine")
def list_own(actor: User = Depends(get_current_user), service: ReservationService = Depends(get_service)):
    return {"data": [reservation_response(item) for item in run_reservation_action(lambda: service.list_own(actor))]}


@router.get("/institution")
def list_institution(actor: User = Depends(get_current_user), service: ReservationService = Depends(get_service)):
    return {"data": [reservation_response(item) for item in run_reservation_action(lambda: service.list_institution(actor))]}


@router.get("/{reservation_id}")
def detail(
    reservation_id: str, response: Response,
    actor: User = Depends(get_current_user), service: ReservationService = Depends(get_service),
):
    item, history = run_reservation_action(lambda: service.detail(actor, reservation_id))
    response.headers["Cache-Control"] = "private, no-store"
    return {"data": {
        **reservation_response(item),
        "reviewed_by": item.reservation.reviewed_by,
        "available_decisions": review_decisions(item.reservation.status),
        "history": [asdict(event) for event in history],
    }}


@router.put("/{reservation_id}")
def edit(
    reservation_id: str, payload: ReservationPayload,
    actor: User = Depends(get_current_user), service: ReservationService = Depends(get_service),
):
    return {"data": reservation_response(run_reservation_action(lambda: service.edit(actor, reservation_id, payload.to_request())))}


@router.post("/{reservation_id}/cancel")
def cancel(
    reservation_id: str, actor: User = Depends(get_current_user), service: ReservationService = Depends(get_service),
):
    return {"data": reservation_response(run_reservation_action(lambda: service.cancel(actor, reservation_id)))}


@router.patch("/{reservation_id}/decision")
def review(
    reservation_id: str, payload: DecisionPayload,
    actor: User = Depends(get_current_user), service: ReservationService = Depends(get_service),
):
    return {"data": reservation_response(run_reservation_action(lambda: service.review(actor, reservation_id, payload.status, payload.reason)))}


def reservation_response(details: ReservationDetails) -> dict:
    item = details.reservation
    request = item.request
    return {
        "id": item.id, "space_id": request.space_id, "space_name": details.space_name,
        "requester_name": details.requester_name, "title": request.title, "activity_type": request.activity_type,
        "start": request.period.start, "end": request.period.end, "participants": request.participants,
        "justification": request.justification, "status": item.status, "has_overlap": details.has_overlap,
        "created_at": item.created_at, "reviewed_at": item.reviewed_at, "decision_reason": item.decision_reason,
    }


def run_reservation_action(action):
    try:
        return action()
    except DomainAuthorizationError as exc:
        raise HTTPException(403, str(exc)) from None
    except ResourceNotFound as exc:
        raise HTTPException(404, str(exc)) from None
    except DuplicateResource as exc:
        raise HTTPException(409, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
