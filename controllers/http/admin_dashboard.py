from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from application.read_models.admin_dashboard import AdminDashboardMetrics
from application.services.admin_dashboard_service import AdminDashboardService
from controllers.http.dependencies import get_admin_dashboard_service, get_current_user
from models.domain.entities.profile import Profile
from models.domain.entities.user import User
from models.domain.exceptions import DomainAuthorizationError


router = APIRouter(prefix="/admin/dashboard", tags=["admin dashboard"])


class EntityCountsResponse(BaseModel):
    total: int
    active: int
    inactive: int


class ProfileCountResponse(BaseModel):
    profile: Profile
    count: int


class RecentUserResponse(BaseModel):
    id: str
    name: str
    email: str
    profile: Profile
    active: bool
    created_at: datetime


class AdminDashboardResponse(BaseModel):
    institution_id: str
    period_days: int
    users: EntityCountsResponse
    users_by_profile: list[ProfileCountResponse]
    recent_user_count: int
    recent_users: list[RecentUserResponse]
    buildings: EntityCountsResponse
    floors: EntityCountsResponse
    spaces: EntityCountsResponse
    resources: EntityCountsResponse


@router.get("", response_model=AdminDashboardResponse)
def get_admin_dashboard(
    period_days: int = Query(default=30, ge=1, le=365),
    actor: User = Depends(get_current_user),
    service: AdminDashboardService = Depends(get_admin_dashboard_service),
) -> AdminDashboardResponse:
    try:
        metrics = service.get_metrics(actor, period_days)
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _response(metrics)


def _response(metrics: AdminDashboardMetrics) -> AdminDashboardResponse:
    def counts(value):
        return EntityCountsResponse(
            total=value.total, active=value.active, inactive=value.inactive
        )

    return AdminDashboardResponse(
        institution_id=metrics.institution_id,
        period_days=metrics.period_days,
        users=counts(metrics.users),
        users_by_profile=[
            ProfileCountResponse(profile=row.profile, count=row.count)
            for row in metrics.users_by_profile
        ],
        recent_user_count=metrics.recent_user_count,
        recent_users=[
            RecentUserResponse(
                id=row.id,
                name=row.name,
                email=row.email,
                profile=row.profile,
                active=row.active,
                created_at=row.created_at,
            )
            for row in metrics.recent_users
        ],
        buildings=counts(metrics.buildings),
        floors=counts(metrics.floors),
        spaces=counts(metrics.spaces),
        resources=counts(metrics.resources),
    )
