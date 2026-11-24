from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from application.services.institution_management_service import (
    InstitutionManagementService,
    InstitutionRegistration,
    InstitutionUpdate,
)
from controllers.http.dependencies import (
    get_current_user,
    get_institution_invite_code_service,
    get_institution_management_service,
)
from application.services.institution_invite_code_service import InstitutionInviteCodeService
from models.domain.entities.institution import (
    ConflictPreferences,
    Institution,
    InstitutionPreferences,
    NotificationPreferences,
    ReservationPreferences,
)
from models.domain.entities.user import User
from models.domain.exceptions import (
    DomainAuthorizationError,
    DuplicateResource,
    ResourceNotFound,
)


router = APIRouter(prefix="/institutions", tags=["institutions"])
registration_router = APIRouter(prefix="/institutions", tags=["institutions"])


class InstitutionRegistrationRequest(BaseModel):
    responsible_name: str = Field(min_length=1, max_length=150)
    responsible_email: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=1024)
    name: str = Field(min_length=1, max_length=180)
    cnpj: str | None = Field(default=None, max_length=18)
    institution_type: str = Field(min_length=1, max_length=80)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=2)
    phone: str = Field(default="", max_length=30)
    email: str = Field(default="", max_length=255)


class ReservationPreferencesRequest(BaseModel):
    min_advance: int = Field(ge=1, le=365)
    min_advance_unit: str
    max_advance: int = Field(ge=1, le=520)
    max_advance_unit: str
    allowed_start: str
    allowed_end: str
    automatic_approval: str
    justification_required: bool


class ConflictPreferencesRequest(BaseModel):
    resolution_criterion: str
    notification_timing: str
    suggest_alternatives: bool


class NotificationPreferencesRequest(BaseModel):
    reservation_approved: bool
    reservation_rejected: bool
    conflict_detected: bool
    space_changed: bool
    reservation_cancelled: bool
    reservation_reminder: bool


class InstitutionPreferencesRequest(BaseModel):
    reservations: ReservationPreferencesRequest
    conflicts: ConflictPreferencesRequest
    notifications: NotificationPreferencesRequest


class InstitutionUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    institution_type: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=2)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=240)
    timezone: str | None = None
    preferences: InstitutionPreferencesRequest | None = None


class InstitutionResponse(BaseModel):
    id: str
    name: str
    cnpj: str | None
    institution_type: str | None
    city: str | None
    state: str | None
    phone: str | None
    email: str | None
    address: str | None
    timezone: str
    preferences: InstitutionPreferencesRequest


class RegisteredOwnerResponse(BaseModel):
    id: str
    name: str
    email: str
    profile: str
    status: str


class InstitutionRegistrationData(BaseModel):
    institution: InstitutionResponse
    administrator: RegisteredOwnerResponse
    invitation_code: str


class RegistrationResponse(BaseModel):
    data: InstitutionRegistrationData


class SingleInstitutionResponse(BaseModel):
    data: InstitutionResponse


@registration_router.post("/signup", response_model=RegistrationResponse, status_code=201)
def register_institution(
    payload: InstitutionRegistrationRequest,
    response: Response,
    service: InstitutionManagementService = Depends(get_institution_management_service),
    invitation_codes: InstitutionInviteCodeService = Depends(get_institution_invite_code_service),
) -> RegistrationResponse:
    try:
        institution, owner, code = service.register_with_invitation(
            InstitutionRegistration(**payload.model_dump()), invitation_codes,
        )
    except DuplicateResource as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    response.headers["Cache-Control"] = "private, no-store"
    return RegistrationResponse(data=InstitutionRegistrationData(
        institution=_institution_response(institution),
        administrator=RegisteredOwnerResponse(
            id=owner.id,
            name=owner.name,
            email=owner.email,
            profile=owner.profile.value,
            status=owner.status.value,
        ),
        invitation_code=code,
    ))


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
            actor,
            InstitutionUpdate(
                **{
                    **payload.model_dump(exclude={"preferences"}),
                    "preferences": _preferences_from_request(payload.preferences),
                }
            ),
        )
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except ResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
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
        address=institution.address,
        timezone=institution.timezone,
        preferences=InstitutionPreferencesRequest(
            reservations=ReservationPreferencesRequest(**{
                field: getattr(institution.preferences.reservations, field)
                for field in ReservationPreferences.__dataclass_fields__
            }),
            conflicts=ConflictPreferencesRequest(**{
                field: getattr(institution.preferences.conflicts, field)
                for field in ConflictPreferences.__dataclass_fields__
            }),
            notifications=NotificationPreferencesRequest(**{
                field: getattr(institution.preferences.notifications, field)
                for field in NotificationPreferences.__dataclass_fields__
            }),
        ),
    )


def _preferences_from_request(
    payload: InstitutionPreferencesRequest | None,
) -> InstitutionPreferences | None:
    if payload is None:
        return None
    try:
        return InstitutionPreferences(
            reservations=ReservationPreferences(**payload.reservations.model_dump()),
            conflicts=ConflictPreferences(**payload.conflicts.model_dump()),
            notifications=NotificationPreferences(**payload.notifications.model_dump()),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
