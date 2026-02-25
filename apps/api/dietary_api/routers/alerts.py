from fastapi import APIRouter, Depends, Request

from ..routes_shared import current_session, get_context, require_scopes
from ..schemas import AlertTimelineResponse, AlertTriggerRequest, AlertTriggerResponse
from ..services.alerts import get_alert_timeline, trigger_alert

router = APIRouter(tags=["alerts"])


@router.post("/api/v1/alerts/trigger", response_model=AlertTriggerResponse)
def alerts_trigger(
    payload: AlertTriggerRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> AlertTriggerResponse:
    require_scopes(session, {"alert:trigger"})
    return trigger_alert(context=get_context(request), session=session, payload=payload)


@router.get("/api/v1/alerts/{alert_id}/timeline", response_model=AlertTimelineResponse)
def alerts_timeline(
    alert_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> AlertTimelineResponse:
    require_scopes(session, {"alert:timeline:read"})
    return get_alert_timeline(context=get_context(request), alert_id=alert_id)
