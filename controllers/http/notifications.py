from dataclasses import asdict

from fastapi import APIRouter, Depends, Query, Request, Response

from application.services.notification_service import NotificationService
from controllers.http.dependencies import get_current_user
from controllers.http.reservations import run_reservation_action
from models.domain.entities.user import User


router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_service(request: Request) -> NotificationService:
    return request.app.state.notification_service


@router.get("")
def inbox(
    response: Response,
    unread_only: bool = False,
    category: str | None = Query(default=None, min_length=1, max_length=30),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    actor: User = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
):
    items, total, unread_count, timezone = run_reservation_action(lambda: service.inbox(
        actor, unread_only=unread_only, category=category, limit=limit, offset=offset,
    ))
    response.headers["Cache-Control"] = "private, no-store"
    return {"data": {
        "items": [asdict(item) for item in items], "total": total, "unread_count": unread_count, "timezone": timezone,
    }}


@router.get("/unread-count")
def unread_count(
    response: Response,
    actor: User = Depends(get_current_user), service: NotificationService = Depends(get_service),
):
    response.headers["Cache-Control"] = "private, no-store"
    return {"data": {"unread_count": run_reservation_action(lambda: service.unread_count(actor))}}


@router.patch("/read")
def mark_all_read(actor: User = Depends(get_current_user), service: NotificationService = Depends(get_service)):
    return {"data": {"updated": run_reservation_action(lambda: service.mark_all_read(actor))}}


@router.patch("/{notification_id}/read")
def mark_read(
    notification_id: str,
    actor: User = Depends(get_current_user), service: NotificationService = Depends(get_service),
):
    return {"data": {"read_at": run_reservation_action(lambda: service.mark_read(actor, notification_id))}}
