
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from application.services.reservation_type_service import ReservationTypeService
from controllers.http.dependencies import (
    get_current_user,
    get_reservation_type_management_service,
)
from models.domain.entities.reservation_type import ReservationType
from models.domain.entities.user import User
from models.domain.exceptions import (
    DomainAuthorizationError,
    DuplicateResource,
    ResourceNotFound,
)


router = APIRouter(
    prefix="/admin/reservation-types",
    tags=["reservation types"],
)


class ReservationTypeResponse(BaseModel):
    id: str
    institution_id: str
    name: str
    description: str
    active: bool


class ReservationTypeListResponse(BaseModel):
    data: list[ReservationTypeResponse]


class SingleReservationTypeResponse(BaseModel):
    data: ReservationTypeResponse


class CreateReservationTypeRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=255)


class UpdateReservationTypeRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=255)


class UpdateReservationTypeStatusRequest(BaseModel):
    active: bool


@router.get("", response_model=ReservationTypeListResponse)
def list_reservation_types(
    include_inactive: bool = Query(default=False),
    actor: User = Depends(get_current_user),
    service: ReservationTypeService = Depends(
        get_reservation_type_management_service
    ),
) -> ReservationTypeListResponse:
    try:
        types = service.list_types(actor, include_inactive)
    except DomainAuthorizationError as exc:
        _raise_http_error(403, str(exc))

    return ReservationTypeListResponse(
        data=[_type_response(item) for item in types]
    )


@router.post("", response_model=SingleReservationTypeResponse, status_code=201)
def create_reservation_type(
    payload: CreateReservationTypeRequest,
    actor: User = Depends(get_current_user),
    service: ReservationTypeService = Depends(
        get_reservation_type_management_service
    ),
) -> SingleReservationTypeResponse:
    try:
        item = service.create_type(
            actor, payload.name, payload.description
        )
    except DomainAuthorizationError as exc:
        _raise_http_error(403, str(exc))
    except DuplicateResource as exc:
        _raise_http_error(409, str(exc))
    except ValueError as exc:
        _raise_http_error(422, str(exc))

    return SingleReservationTypeResponse(data=_type_response(item))


@router.get("/{type_id}", response_model=SingleReservationTypeResponse)
def get_reservation_type(
    type_id: str,
    actor: User = Depends(get_current_user),
    service: ReservationTypeService = Depends(
        get_reservation_type_management_service
    ),
) -> SingleReservationTypeResponse:
    try:
        item = service.get_type(actor, type_id)
    except DomainAuthorizationError as exc:
        _raise_http_error(403, str(exc))
    except ResourceNotFound as exc:
        _raise_http_error(404, str(exc))

    return SingleReservationTypeResponse(data=_type_response(item))


@router.patch("/{type_id}", response_model=SingleReservationTypeResponse)
def update_reservation_type(
    type_id: str,
    payload: UpdateReservationTypeRequest,
    actor: User = Depends(get_current_user),
    service: ReservationTypeService = Depends(
        get_reservation_type_management_service
    ),
) -> SingleReservationTypeResponse:
    try:
        item = service.update_type(
            actor, type_id, payload.name, payload.description
        )
    except DomainAuthorizationError as exc:
        _raise_http_error(403, str(exc))
    except ResourceNotFound as exc:
        _raise_http_error(404, str(exc))
    except DuplicateResource as exc:
        _raise_http_error(409, str(exc))
    except ValueError as exc:
        _raise_http_error(422, str(exc))

    return SingleReservationTypeResponse(data=_type_response(item))


@router.patch("/{type_id}/status", response_model=SingleReservationTypeResponse)
def update_reservation_type_status(
    type_id: str,
    payload: UpdateReservationTypeStatusRequest,
    actor: User = Depends(get_current_user),
    service: ReservationTypeService = Depends(
        get_reservation_type_management_service
    ),
) -> SingleReservationTypeResponse:
    try:
        item = service.set_type_active(actor, type_id, payload.active)
    except DomainAuthorizationError as exc:
        _raise_http_error(403, str(exc))
    except ResourceNotFound as exc:
        _raise_http_error(404, str(exc))

    return SingleReservationTypeResponse(data=_type_response(item))


def _type_response(item: ReservationType) -> ReservationTypeResponse:
    return ReservationTypeResponse(
        id=item.id,
        institution_id=item.institution_id,
        name=item.name,
        description=item.description,
        active=item.active,
    )


def _raise_http_error(status_code: int, message: str) -> None:
    raise HTTPException(status_code=status_code, detail=message)
