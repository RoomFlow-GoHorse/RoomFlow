from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from application.services.institution_management_service import (
    InstitutionManagementService,
    InstitutionRegistration,
    InstitutionUpdate,
)
from controllers.http.dependencies import (
    get_current_user,
    get_institution_management_service,
)
from models.domain.entities.institution import Institution
from models.domain.entities.user import User
from models.domain.exceptions import (
    DomainAuthorizationError,
    DuplicateResource,
    ResourceNotFound,
)


router = APIRouter(prefix="/institutions", tags=["institutions"])


class InstitutionRegistrationRequest(BaseModel):
    responsible_name: str = Field(min_length=1, max_length=150)
    responsible_email: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=6, max_length=1024)
    name: str = Field(min_length=1, max_length=180)
    cnpj: str = Field(min_length=11, max_length=18)
    institution_type: str = Field(min_length=1, max_length=80)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=2)
    phone: str = Field(default="", max_length=30)
    email: str = Field(default="", max_length=255)


class InstitutionUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    institution_type: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=2)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)


class InstitutionResponse(BaseModel):
    id: str
    name: str
    cnpj: str | None
    institution_type: str | None
    city: str | None
    state: str | None
    phone: str | None
    email: str | None


class RegisteredOwnerResponse(BaseModel):
    id: str
    name: str
    email: str
    profile: str
    status: str


class RegistrationResponse(BaseModel):
    data: dict[str, InstitutionResponse | RegisteredOwnerResponse]


class SingleInstitutionResponse(BaseModel):
    data: InstitutionResponse


@router.post("/signup", response_model=RegistrationResponse, status_code=201)
def register_institution(
    payload: InstitutionRegistrationRequest,
    service: InstitutionManagementService = Depends(get_institution_management_service),
) -> RegistrationResponse:
    try:
        institution, owner = service.register(InstitutionRegistration(**payload.model_dump()))
    except DuplicateResource as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return RegistrationResponse(data={
        "institution": _institution_response(institution),
        "administrator": RegisteredOwnerResponse(
            id=owner.id,
            name=owner.name,
            email=owner.email,
            profile=owner.profile.value,
            status=owner.status.value,
        ),
    })


@router.get("/me", response_model=SingleInstitutionResponse)
def get_own_institution(
    actor: User = Depends(get_current_user),
    service: InstitutionManagementService = Depends(get_institution_management_service),
) -> SingleInstitutionResponse:
    try:
        institution = service.get_own(actor)
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except ResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return SingleInstitutionResponse(data=_institution_response(institution))


@router.patch("/me", response_model=SingleInstitutionResponse)
def update_own_institution(
    payload: InstitutionUpdateRequest,
    actor: User = Depends(get_current_user),
    service: InstitutionManagementService = Depends(get_institution_management_service),
) -> SingleInstitutionResponse:
    try:
        institution = service.update_own(
            actor, InstitutionUpdate(**payload.model_dump())
        )
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except ResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return SingleInstitutionResponse(data=_institution_response(institution))


def _institution_response(institution: Institution) -> InstitutionResponse:
    return InstitutionResponse(
        id=institution.id,
        name=institution.name,
        cnpj=institution.cnpj,
        institution_type=institution.institution_type,
        city=institution.city,
        state=institution.state,
        phone=institution.phone,
        email=institution.email,
    )
