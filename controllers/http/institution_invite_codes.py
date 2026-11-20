from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from application.services.institution_invite_code_service import InstitutionInviteCodeService
from controllers.http.dependencies import get_current_user, get_institution_invite_code_service
from models.domain.entities.user import User
from models.domain.exceptions import DomainAuthorizationError


router = APIRouter(prefix="/institutions/me/invitation-code", tags=["institution invitations"])


class InvitationCodeStatusResponse(BaseModel):
    data: dict[str, bool | datetime | None]


class IssuedInvitationCodeResponse(BaseModel):
    data: dict[str, str | datetime | bool]


@router.get("", response_model=InvitationCodeStatusResponse)
def get_invitation_code_status(
    institution_id: str | None = Query(default=None, max_length=100),
    actor: User = Depends(get_current_user),
    service: InstitutionInviteCodeService = Depends(get_institution_invite_code_service),
) -> InvitationCodeStatusResponse:
    try:
        status = service.status_for(actor, institution_id)
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    # The secret cannot be recovered: only the digest is stored.
    return InvitationCodeStatusResponse(data={"active": status.active, "created_at": status.created_at})


@router.post("/rotate", response_model=IssuedInvitationCodeResponse)
def rotate_invitation_code(
    institution_id: str | None = Query(default=None, max_length=100),
    actor: User = Depends(get_current_user),
    service: InstitutionInviteCodeService = Depends(get_institution_invite_code_service),
) -> IssuedInvitationCodeResponse:
    try:
        raw_code, status = service.issue_or_replace(actor, institution_id)
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    return IssuedInvitationCodeResponse(data={
        "code": raw_code,
        "active": status.active,
        "created_at": status.created_at,
    })
