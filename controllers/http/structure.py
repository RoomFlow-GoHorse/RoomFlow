from typing import Generic, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from application.services.space_service import SpaceService
from controllers.http.dependencies import get_current_user, get_space_management_service
from models.domain.entities.building import Building
from models.domain.entities.floor import Floor
from models.domain.entities.space import Space
from models.domain.entities.user import User
from models.domain.exceptions import DomainAuthorizationError, DuplicateResource, ResourceNotFound


router = APIRouter(prefix="/structure", tags=["institution structure"])
T = TypeVar("T")


class BuildingRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class FloorRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class SpaceCreateRequest(BaseModel):
    floor_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=120)
    type: str = Field(min_length=1, max_length=80)
    capacity: int = Field(ge=1, le=10000, strict=True)
    status: str = "disponivel"


class SpaceUpdateRequest(BaseModel):
    floor_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    type: str | None = Field(default=None, min_length=1, max_length=80)
    capacity: int | None = Field(default=None, ge=1, le=10000, strict=True)
    status: str | None = None


class ActiveRequest(BaseModel):
    active: bool


class BuildingResponse(BaseModel):
    id: str
    institution_id: str
    name: str
    active: bool


class FloorResponse(BaseModel):
    id: str
    building_id: str
    name: str
    active: bool


class SpaceResponse(BaseModel):
    id: str
    institution_id: str
    building_id: str
    floor_id: str
    name: str
    type: str
    capacity: int
    building: str
    floor: str
    location: str
    status: str
    active: bool


class ListResponse(BaseModel, Generic[T]):
    data: list[T]


class ItemResponse(BaseModel, Generic[T]):
    data: T


@router.get("/buildings", response_model=ListResponse[BuildingResponse])
def list_buildings(
    include_inactive: bool = False,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    return ListResponse(data=[_building(item) for item in _run(lambda: service.list_buildings(actor, include_inactive))])


@router.get("/buildings/{building_id}", response_model=ItemResponse[BuildingResponse])
def get_building(
    building_id: str,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    return ItemResponse(data=_building(_run(lambda: service.get_building(actor, building_id))))


@router.post("/buildings", response_model=ItemResponse[BuildingResponse], status_code=201)
def create_building(
    payload: BuildingRequest,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    return ItemResponse(data=_building(_run(lambda: service.create_building(actor, payload.name))))


@router.patch("/buildings/{building_id}", response_model=ItemResponse[BuildingResponse])
def update_building(
    building_id: str,
    payload: BuildingRequest,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    return ItemResponse(data=_building(_run(lambda: service.update_building(actor, building_id, payload.name))))


@router.patch("/buildings/{building_id}/status", response_model=ItemResponse[BuildingResponse])
def set_building_status(
    building_id: str,
    payload: ActiveRequest,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    result = _run(lambda: service.activate_building(actor, building_id) if payload.active else service.deactivate_building(actor, building_id))
    return ItemResponse(data=_building(result))


@router.get("/buildings/{building_id}/floors", response_model=ListResponse[FloorResponse])
def list_floors(
    building_id: str,
    include_inactive: bool = False,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    return ListResponse(data=[_floor(item) for item in _run(lambda: service.list_floors(actor, building_id, include_inactive))])


@router.get("/floors/{floor_id}", response_model=ItemResponse[FloorResponse])
def get_floor(
    floor_id: str,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    return ItemResponse(data=_floor(_run(lambda: service.get_floor(actor, floor_id))))


@router.post("/buildings/{building_id}/floors", response_model=ItemResponse[FloorResponse], status_code=201)
def create_floor(
    building_id: str,
    payload: FloorRequest,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    return ItemResponse(data=_floor(_run(lambda: service.create_floor(actor, building_id, payload.name))))


@router.patch("/floors/{floor_id}", response_model=ItemResponse[FloorResponse])
def update_floor(
    floor_id: str,
    payload: FloorRequest,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    return ItemResponse(data=_floor(_run(lambda: service.update_floor(actor, floor_id, payload.name))))


@router.patch("/floors/{floor_id}/status", response_model=ItemResponse[FloorResponse])
def set_floor_status(
    floor_id: str,
    payload: ActiveRequest,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    result = _run(lambda: service.activate_floor(actor, floor_id) if payload.active else service.deactivate_floor(actor, floor_id))
    return ItemResponse(data=_floor(result))


@router.get("/spaces", response_model=ListResponse[SpaceResponse])
def list_institution_spaces(
    q: str = Query(default="", max_length=120),
    status: str | None = None,
    building_id: str | None = None,
    floor_id: str | None = None,
    include_inactive: bool = False,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    items = _run(lambda: service.list_spaces(actor, q, status, building_id, floor_id, include_inactive))
    return ListResponse(data=[_space(item) for item in items])


@router.get("/spaces/{space_id}", response_model=ItemResponse[SpaceResponse])
def get_space(
    space_id: str,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    return ItemResponse(data=_space(_run(lambda: service.get_space(actor, space_id))))


@router.post("/spaces", response_model=ItemResponse[SpaceResponse], status_code=201)
def create_space(
    payload: SpaceCreateRequest,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    result = _run(lambda: service.create_space(actor, payload.floor_id, payload.name, payload.type, payload.capacity, payload.status))
    return ItemResponse(data=_space(result))


@router.patch("/spaces/{space_id}", response_model=ItemResponse[SpaceResponse])
def update_space(
    space_id: str,
    payload: SpaceUpdateRequest,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    changes = payload.model_dump(exclude_unset=True)
    if "type" in changes:
        changes["room_type"] = changes.pop("type")
    result = _run(lambda: service.update_space(actor, space_id, **changes))
    return ItemResponse(data=_space(result))


@router.patch("/spaces/{space_id}/status", response_model=ItemResponse[SpaceResponse])
def set_space_status(
    space_id: str,
    payload: ActiveRequest,
    actor: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_management_service),
):
    result = _run(lambda: service.activate_space(actor, space_id) if payload.active else service.deactivate_space(actor, space_id))
    return ItemResponse(data=_space(result))


def _run(action):
    try:
        return action()
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except ResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except DuplicateResource as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


def _building(item: Building) -> BuildingResponse:
    return BuildingResponse(id=item.id, institution_id=item.institution_id, name=item.name, active=item.active)


def _floor(item: Floor) -> FloorResponse:
    return FloorResponse(id=item.id, building_id=item.building_id, name=item.name, active=item.active)


def _space(item: Space) -> SpaceResponse:
    return SpaceResponse(
        id=item.id, institution_id=item.institution_id, building_id=item.building_id,
        floor_id=item.floor_id, name=item.name, type=item.type, capacity=item.capacity,
        building=item.building, floor=item.floor, location=item.location,
        status=item.status, active=item.active,
    )
