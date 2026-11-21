from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from application.ports.email_sender import EmailDeliveryUnavailable

from application.services.enrollment_management_service import (
    EnrollmentManagementService,
    MemberIdentityNotConfirmed,
    TooManyEnrollmentAttempts,
)
from application.services.member_signup_service import (
    InvalidEmailVerification,
    MemberSignupService,
)
from controllers.http.dependencies import (
    get_enrollment_management_service,
    get_member_signup_service,
)
from models.domain.exceptions import DuplicateResource


router = APIRouter(prefix="/auth/signup/member", tags=["member registration"])


class MemberInstitutionPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    registration_number: str = Field(min_length=1, max_length=100)
    institutional_code: str = Field(min_length=1, max_length=200)


class MemberInstitutionPreviewResponse(BaseModel):
    data: dict[str, str]


class MemberSignupStartRequest(MemberInstitutionPreviewRequest):
    password: str = Field(min_length=8, max_length=1024)


class MemberSignupStartResponse(BaseModel):
    data: dict[str, str]


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=20, max_length=200)


class MemberSignupCompleteResponse(BaseModel):
    data: dict[str, str]


@router.post("/preview", response_model=MemberInstitutionPreviewResponse)
def preview_member_institution(
    payload: MemberInstitutionPreviewRequest,
    request: Request,
    service: EnrollmentManagementService = Depends(get_enrollment_management_service),
) -> MemberInstitutionPreviewResponse:
    attempt_key = request.client.host if request.client else "local"
    try:
        preview = service.preview_member_institution(
            payload.institutional_code,
            payload.registration_number,
            payload.name,
            payload.email,
            attempt_key,
        )
    except MemberIdentityNotConfirmed:
        raise HTTPException(
            status_code=400,
            detail="Não foi possível confirmar os dados informados.",
        ) from None
    except TooManyEnrollmentAttempts:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Aguarde e tente novamente.",
            headers={"Retry-After": "60"},
        ) from None
    return MemberInstitutionPreviewResponse(
        data={"institution_name": preview.institution_name}
    )


@router.post("/start", response_model=MemberSignupStartResponse, status_code=202)
def start_member_signup(
    payload: MemberSignupStartRequest,
    request: Request,
    service: MemberSignupService = Depends(get_member_signup_service),
) -> MemberSignupStartResponse:
    attempt_key = request.client.host if request.client else "local"
    try:
        started = service.start(
            name=payload.name,
            email=payload.email,
            registration_number=payload.registration_number,
            institutional_code=payload.institutional_code,
            password=payload.password,
            attempt_key=attempt_key,
        )
    except MemberIdentityNotConfirmed:
        raise HTTPException(status_code=400, detail="N\u00e3o foi poss\u00edvel concluir o cadastro com os dados informados.") from None
    except DuplicateResource:
        raise HTTPException(status_code=400, detail="N\u00e3o foi poss\u00edvel concluir o cadastro com os dados informados.") from None
    except TooManyEnrollmentAttempts:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde e tente novamente.", headers={"Retry-After": "60"}) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except EmailDeliveryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    return MemberSignupStartResponse(data={
        "institution_name": started.institution_name,
        "email": started.email,
        "status": "verification_sent",
    })


@router.post("/verify-email", response_model=MemberSignupCompleteResponse)
def verify_member_email(
    payload: VerifyEmailRequest,
    request: Request,
    service: MemberSignupService = Depends(get_member_signup_service),
) -> MemberSignupCompleteResponse:
    attempt_key = request.client.host if request.client else "local"
    try:
        registered = service.verify_email(payload.token, attempt_key)
    except TooManyEnrollmentAttempts:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde e tente novamente.", headers={"Retry-After": "60"}) from None
    except InvalidEmailVerification:
        raise HTTPException(status_code=400, detail="Token inv\u00e1lido, expirado ou j\u00e1 utilizado.") from None
    return MemberSignupCompleteResponse(data={
        "id": registered.user.id,
        "name": registered.user.name,
        "email": registered.user.email,
        "profile": registered.user.profile.value,
        "institution_id": registered.user.institution_id or "",
        "status": registered.user.status.value,
    })
