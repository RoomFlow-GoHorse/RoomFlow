from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from controllers.http.dependencies import get_space_service
from application.services.space_service import SpaceService


class SpaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: str
    capacity: int
    building: str
    floor: str
    location: str
    status: str
    resources: list[str]
    occupancy: int


class SpaceListResponse(BaseModel):
    data: list[SpaceResponse]


router = APIRouter(prefix="/spaces", tags=["spaces"])


@router.get("", response_model=SpaceListResponse)
def list_spaces(
    service: SpaceService = Depends(get_space_service),
) -> SpaceListResponse:
    return SpaceListResponse(data=service.list_spaces())
