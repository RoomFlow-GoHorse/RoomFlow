from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from application.services.enrollment_management_service import (
    EnrollmentManagementService,
    MemberIdentityNotConfirmed,
    TooManyEnrollmentAttempts,
)
from controllers.http.dependencies import get_enrollment_management_service


router = APIRouter(prefix="/auth/signup/member", tags=["member registration"])


class MemberInstitutionPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    registration_number: str = Field(min_length=1, max_length=100)
    institutional_code: str = Field(min_length=1, max_length=200)


class MemberInstitutionPreviewResponse(BaseModel):
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
