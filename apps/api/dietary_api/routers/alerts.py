"""API router for alerts endpoints."""

from fastapi import APIRouter, Depends, Request

from ..deps import alert_deps
from ..routes_shared import current_session, get_context, require_action
from ..schemas import AlertTimelineResponse, AlertTriggerRequest, AlertTriggerResponse
from ..services.alerts import get_alert_timeline, trigger_alert

router = APIRouter(tags=["alerts"])


@router.post("/api/v1/alerts/trigger", response_model=AlertTriggerResponse)
def alerts_trigger(
    payload: AlertTriggerRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> AlertTriggerResponse:
    require_action(session, "alerts.trigger")
    return trigger_alert(
        deps=alert_deps(get_context(request)),
        session=session,
        payload=payload,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/api/v1/alerts/{alert_id}/timeline", response_model=AlertTimelineResponse)
def alerts_timeline(
    alert_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> AlertTimelineResponse:
    require_action(session, "alerts.timeline.read")
    return get_alert_timeline(deps=alert_deps(get_context(request)), alert_id=alert_id)
