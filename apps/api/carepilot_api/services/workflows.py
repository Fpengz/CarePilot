"""Workflow trace query services (API layer)."""

from __future__ import annotations

from apps.api.carepilot_api.deps import WorkflowDeps
from apps.api.carepilot_api.schemas.workflows import (
    WorkflowListItem,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowTimelineEventPayloadResponse,
    WorkflowTimelineEventResponse,
)
from care_pilot.features.workflows.query_service import (
    list_workflow_runs,
    replay_workflow,
)
from care_pilot.platform.observability.workflows.domain.models import (
    WorkflowTimelineEvent,
)


def _timeline_event_response(
    event: WorkflowTimelineEvent,
) -> WorkflowTimelineEventResponse:
    payload = event.model_dump(mode="json")
    return WorkflowTimelineEventResponse(
        event_id=str(payload["event_id"]),
        event_type=str(payload["event_type"]),
        workflow_name=(
            str(payload["workflow_name"])
            if payload.get("workflow_name") is not None
            else None
        ),
        request_id=(
            str(payload["request_id"])
            if payload.get("request_id") is not None
            else None
        ),
        correlation_id=str(payload["correlation_id"]),
        user_id=(
            str(payload["user_id"])
            if payload.get("user_id") is not None
            else None
        ),
        payload=WorkflowTimelineEventPayloadResponse.model_validate(
            dict(payload.get("payload") or {})
        ),
        created_at=payload["created_at"],
    )


def list_workflows(*, deps: WorkflowDeps) -> WorkflowListResponse:
    summaries = list_workflow_runs(event_timeline=deps.event_timeline)
    return WorkflowListResponse(
        items=[
            WorkflowListItem(
                correlation_id=item.correlation_id,
                request_id=item.request_id,
                user_id=item.user_id,
                workflow_name=item.workflow_name,
                created_at=item.created_at,
                latest_event_at=item.latest_event_at,
                event_count=item.event_count,
            )
            for item in summaries
        ]
    )


def get_workflow(
    *, deps: WorkflowDeps, correlation_id: str
) -> WorkflowResponse:
    workflow = replay_workflow(
        event_timeline=deps.event_timeline, correlation_id=correlation_id
    )
    return WorkflowResponse(
        workflow_name=str(workflow.workflow_name),
        request_id=workflow.request_id,
        correlation_id=workflow.correlation_id,
        replayed=workflow.replayed,
        timeline_events=[
            _timeline_event_response(event)
            for event in workflow.timeline_events
        ],
    )


__all__ = ["get_workflow", "list_workflows"]
