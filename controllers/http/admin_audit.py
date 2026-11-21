from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict

from application.services.admin_audit_service import AdminAuditService
from controllers.http.dependencies import get_admin_audit_service, get_current_user
from models.domain.entities.admin_audit_event import AdminAuditAction
from models.domain.entities.user import User
from models.domain.exceptions import DomainAuthorizationError


router = APIRouter(prefix="/admin/audit", tags=["administrative audit"])


class AdminAuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    actor_user_id: str
    actor_name: str
    action: AdminAuditAction
    resource_type: str
    resource_id: str
    occurred_at: datetime


class AdminAuditListResponse(BaseModel):
    data: list[AdminAuditEventResponse]


@router.get("", response_model=AdminAuditListResponse)
def list_admin_audit_events(
    response: Response,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    action: AdminAuditAction | None = None,
    actor_user_id: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=200, ge=1, le=500),
    actor: User = Depends(get_current_user),
    service: AdminAuditService = Depends(get_admin_audit_service),
) -> AdminAuditListResponse:
    try:
        events = service.list_events(
            actor,
            start_at=start_at,
            end_at=end_at,
            action=action,
            actor_user_id=actor_user_id,
            limit=limit,
        )
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    response.headers["Cache-Control"] = "private, no-store"
    return AdminAuditListResponse(data=[AdminAuditEventResponse.model_validate(item) for item in events])
