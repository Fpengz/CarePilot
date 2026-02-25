from fastapi import APIRouter, Depends, HTTPException, Request

from ..routes_shared import current_session, get_context
from ..schemas import (
    NotificationListResponse,
    NotificationMarkAllReadResponse,
    NotificationMarkReadResponse,
)
from ..services.notifications import list_notifications, mark_all_notifications_read, mark_notification_read

router = APIRouter(tags=["notifications"])


@router.get("/api/v1/notifications", response_model=NotificationListResponse)
def notifications_list(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> NotificationListResponse:
    return list_notifications(context=get_context(request), user_id=str(session["user_id"]))


@router.post("/api/v1/notifications/{notification_id}/read", response_model=NotificationMarkReadResponse)
def notifications_mark_read(
    notification_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> NotificationMarkReadResponse:
    result = mark_notification_read(
        context=get_context(request),
        user_id=str(session["user_id"]),
        notification_id=notification_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="notification not found")
    return result


@router.post("/api/v1/notifications/read-all", response_model=NotificationMarkAllReadResponse)
def notifications_mark_all_read(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> NotificationMarkAllReadResponse:
    return mark_all_notifications_read(context=get_context(request), user_id=str(session["user_id"]))
