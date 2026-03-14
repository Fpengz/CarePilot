"""Session-scoped alert orchestration use cases.

Wraps the workflow coordinator and alert store to provide the HTTP-facing
``trigger_alert_for_session`` and ``get_alert_timeline`` helpers.
Kept separate from ``alert_dispatch`` to avoid a circular import between
``alert_dispatch`` → ``apps.api.dietary_api.deps`` → ``platform_registry``
→ ``alert_dispatch``.
"""

from __future__ import annotations

from typing import cast
from uuid import uuid4

from apps.api.dietary_api.deps import AlertDeps
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    AlertTimelineResponse,
    AlertTriggerRequest,
    AlertTriggerResponse,
)
from dietary_guardian.platform.auth.session_context import build_user_profile_from_session
from dietary_guardian.platform.observability.tooling.domain.models import ToolPolicyContext
from dietary_guardian.core.contracts.agent_envelopes import AgentHandoff
from dietary_guardian.platform.observability.workflows.domain.models import WorkflowExecutionResult, WorkflowName


def trigger_alert_for_session(
    *,
    deps: AlertDeps,
    session: dict[str, object],
    payload: AlertTriggerRequest,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> AlertTriggerResponse:
    user_profile = build_user_profile_from_session(session, deps.stores.profiles)
    issued_request_id = request_id or str(uuid4())
    issued_correlation_id = correlation_id or str(uuid4())
    deps.event_timeline.append(
        event_type="workflow_started",
        workflow_name=WorkflowName.ALERT_ONLY.value,
        correlation_id=issued_correlation_id,
        request_id=issued_request_id,
        user_id=user_profile.id,
        payload={"alert_type": payload.alert_type, "destinations": payload.destinations},
    )
    tool_result = deps.tool_registry.execute(
        "trigger_alert",
        {
            "alert_type": payload.alert_type,
            "severity": payload.severity,
            "message": payload.message,
            "destinations": payload.destinations,
        },
        ToolPolicyContext(
            account_role=str(session["account_role"]),
            scopes=cast(list[str], session["scopes"]),
            environment="prod",
            user_id=user_profile.id,
            correlation_id=issued_correlation_id,
        ),
    )
    handoffs = [
        AgentHandoff(
            from_agent="care_orchestrator",
            to_agent="notification_agent",
            request_id=issued_request_id,
            correlation_id=issued_correlation_id,
            confidence=1.0 if tool_result.success else 0.0,
            obligations=["deliver_alert_via_channels"],
            payload={"alert_type": payload.alert_type, "destinations": payload.destinations},
        )
    ]
    deps.event_timeline.append(
        event_type="workflow_completed",
        workflow_name=WorkflowName.ALERT_ONLY.value,
        correlation_id=issued_correlation_id,
        request_id=issued_request_id,
        user_id=user_profile.id,
        payload={"tool_success": tool_result.success, "tool_name": tool_result.tool_name},
    )
    workflow = WorkflowExecutionResult(
        workflow_name=WorkflowName.ALERT_ONLY,
        request_id=issued_request_id,
        correlation_id=issued_correlation_id,
        user_id=user_profile.id,
        handoffs=handoffs,
        tool_results=[tool_result],
        timeline_events=deps.event_timeline.get_events(correlation_id=issued_correlation_id),
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
    outbox = deps.stores.alerts.list_alert_records(cast(str | None, alert_id))
    return AlertTriggerResponse(
        tool_result=tool_result,
        outbox_timeline=[item.model_dump(mode="json") for item in outbox],
        workflow=workflow.model_dump(mode="json"),
    )


def get_alert_timeline(*, deps: AlertDeps, alert_id: str) -> AlertTimelineResponse:
    outbox = deps.stores.alerts.list_alert_records(alert_id)
    if not outbox:
        raise build_api_error(status_code=404, code="alerts.not_found", message="alert not found")
    return AlertTimelineResponse(
        alert_id=alert_id,
        outbox_timeline=[item.model_dump(mode="json") for item in outbox],
    )
