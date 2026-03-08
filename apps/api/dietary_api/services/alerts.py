from typing import cast

from apps.api.dietary_api.auth import build_user_profile_from_session
from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import AlertTimelineResponse, AlertTriggerRequest, AlertTriggerResponse


def trigger_alert(
    *,
    context: AppContext,
    session: dict[str, object],
    payload: AlertTriggerRequest,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> AlertTriggerResponse:
    user_profile = build_user_profile_from_session(session, context.stores.profiles)
    workflow = context.coordinator.run_alert_workflow(
        user_profile=user_profile,
        alert_type=payload.alert_type,
        severity=payload.severity,
        message=payload.message,
        destinations=payload.destinations,
        request_id=request_id,
        correlation_id=correlation_id,
        account_role=str(session["account_role"]),
        scopes=cast(list[str], session["scopes"]),
        environment="prod",
    )
    tool_result = workflow.tool_results[0] if workflow.tool_results else None
    if tool_result is None:
        raise build_api_error(
            status_code=500,
            code="alerts.workflow_missing_tool_result",
            message="workflow returned no tool result",
        )
    alert_id = None
    if tool_result.output is not None:
        alert_id = cast(dict[str, object], tool_result.output.model_dump()).get("alert_id")
    outbox = context.stores.alerts.list_alert_records(cast(str | None, alert_id))
    return AlertTriggerResponse(
        tool_result=tool_result.model_dump(mode="json"),
        outbox_timeline=[item.model_dump(mode="json") for item in outbox],
        workflow=workflow.model_dump(mode="json"),
    )


def get_alert_timeline(*, context: AppContext, alert_id: str) -> AlertTimelineResponse:
    outbox = context.stores.alerts.list_alert_records(alert_id)
    if not outbox:
        raise build_api_error(status_code=404, code="alerts.not_found", message="alert not found")
    return AlertTimelineResponse(
        alert_id=alert_id,
        outbox_timeline=[item.model_dump(mode="json") for item in outbox],
    )
