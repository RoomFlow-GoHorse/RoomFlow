from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from application.services.enrollment_management_service import (
    EnrollmentManagementService,
    EnrollmentImportPreview,
)
from controllers.http.dependencies import get_current_user, get_enrollment_management_service
from models.domain.entities.authorized_enrollment import AuthorizedEnrollment, EnrollmentStatus
from models.domain.entities.user import User
from models.domain.exceptions import DomainAuthorizationError, DuplicateResource, ResourceNotFound


router = APIRouter(prefix="/admin/enrollments", tags=["authorized enrollments"])


class EnrollmentResponse(BaseModel):
    id: str
    institution_id: str
    registration_number: str
    name: str | None
    email: str | None
    status: EnrollmentStatus
    used_by_user_id: str | None


class EnrollmentListResponse(BaseModel):
    data: list[EnrollmentResponse]


class SingleEnrollmentResponse(BaseModel):
    data: EnrollmentResponse


class AddEnrollmentRequest(BaseModel):
    registration_number: str = Field(min_length=1, max_length=100)
    name: str | None = Field(default=None, max_length=150)
    email: str | None = Field(default=None, max_length=255)


class ImportRowResponse(BaseModel):
    row_number: int
    registration_number: str | None
    name: str | None
    email: str | None
    status: str
    reason: str | None


class ImportPreviewResponse(BaseModel):
    data: dict[str, object]


class ConfirmImportRequest(BaseModel):
    preview_id: str = Field(min_length=1, max_length=100)


class ConfirmImportResponse(BaseModel):
    data: dict[str, int]


@router.get("", response_model=EnrollmentListResponse)
def list_enrollments(
    q: str = Query(default="", max_length=100),
    status: EnrollmentStatus | None = None,
    institution_id: str | None = Query(default=None, max_length=100),
    actor: User = Depends(get_current_user),
    service: EnrollmentManagementService = Depends(get_enrollment_management_service),
) -> EnrollmentListResponse:
    try:
        results = service.list_enrollments(actor, q, status, institution_id)
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    return EnrollmentListResponse(data=[_enrollment_response(item) for item in results])


@router.post("", response_model=SingleEnrollmentResponse, status_code=201)
def add_enrollment(
    payload: AddEnrollmentRequest,
    actor: User = Depends(get_current_user),
    service: EnrollmentManagementService = Depends(get_enrollment_management_service),
) -> SingleEnrollmentResponse:
    try:
        enrollment = service.add_manual(
            actor, payload.registration_number, payload.name, payload.email
        )
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except DuplicateResource as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return SingleEnrollmentResponse(data=_enrollment_response(enrollment))


@router.delete("/{enrollment_id}", response_model=SingleEnrollmentResponse)
def deactivate_enrollment(
    enrollment_id: str,
    actor: User = Depends(get_current_user),
    service: EnrollmentManagementService = Depends(get_enrollment_management_service),
) -> SingleEnrollmentResponse:
    try:
        enrollment = service.deactivate(actor, enrollment_id)
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except ResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return SingleEnrollmentResponse(data=_enrollment_response(enrollment))


@router.post("/import/preview", response_model=ImportPreviewResponse)
async def preview_import(
    file: UploadFile = File(...),
    actor: User = Depends(get_current_user),
    service: EnrollmentManagementService = Depends(get_enrollment_management_service),
) -> ImportPreviewResponse:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="Envie uma planilha .xlsx.")
    content = await file.read(10 * 1024 * 1024 + 1)
    try:
        preview = service.preview_import(actor, content)
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return ImportPreviewResponse(data=_preview_response(preview))


@router.post("/import/confirm", response_model=ConfirmImportResponse)
def confirm_import(
    payload: ConfirmImportRequest,
    actor: User = Depends(get_current_user),
    service: EnrollmentManagementService = Depends(get_enrollment_management_service),
) -> ConfirmImportResponse:
    try:
        count = service.confirm_import(actor, payload.preview_id)
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except DuplicateResource as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return ConfirmImportResponse(data={"imported": count})


def _enrollment_response(item: AuthorizedEnrollment) -> EnrollmentResponse:
    return EnrollmentResponse(
        id=item.id,
        institution_id=item.institution_id,
        registration_number=item.registration_number,
        name=item.name,
        email=item.email,
        status=item.status,
        used_by_user_id=item.used_by_user_id,
    )


def _preview_response(preview: EnrollmentImportPreview) -> dict[str, object]:
    def rows(items):
        return [
            ImportRowResponse(
                row_number=item.row_number,
                registration_number=item.registration_number,
                name=item.name,
                email=item.email,
                status=item.status,
                reason=item.reason,
            ).model_dump()
            for item in items
        ]

    return {
        "preview_id": preview.preview_id,
        "counts": {
            "valid": len(preview.valid),
            "duplicates": len(preview.duplicates),
            "invalid": len(preview.invalid),
        },
        "valid": rows(preview.valid),
        "duplicates": rows(preview.duplicates),
        "invalid": rows(preview.invalid),
    }
