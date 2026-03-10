"""Workflow replay and listing operations for API endpoints."""

from __future__ import annotations

from apps.api.dietary_api.deps import WorkflowDeps
from apps.api.dietary_api.schemas import WorkflowListItem, WorkflowListResponse, WorkflowResponse
from apps.api.dietary_api.services.workflows_support import timeline_event_response


def get_workflow(*, deps: WorkflowDeps, correlation_id: str) -> WorkflowResponse:
    """Replay a workflow timeline for a single correlation id."""
    workflow = deps.coordinator.replay_workflow(correlation_id)
    return WorkflowResponse(
        workflow_name=str(workflow.workflow_name),
        request_id=workflow.request_id,
        correlation_id=workflow.correlation_id,
        replayed=workflow.replayed,
        timeline_events=[timeline_event_response(event) for event in workflow.timeline_events],
    )



def list_workflows(*, deps: WorkflowDeps) -> WorkflowListResponse:
    """List known workflows grouped by correlation id."""
    events = deps.event_timeline.get_events()
    by_correlation: dict[str, WorkflowListItem] = {}
    for event in events:
        item = by_correlation.get(event.correlation_id)
        if item is None:
            item = WorkflowListItem(
                correlation_id=event.correlation_id,
                request_id=event.request_id,
                user_id=event.user_id,
                workflow_name=event.workflow_name,
                created_at=event.created_at,
                latest_event_at=event.created_at,
                event_count=0,
            )
            by_correlation[event.correlation_id] = item

        item.event_count += 1
        if event.workflow_name and not item.workflow_name:
            item.workflow_name = event.workflow_name
        if event.created_at > item.latest_event_at:
            item.latest_event_at = event.created_at
    items = sorted(by_correlation.values(), key=lambda row: row.latest_event_at, reverse=True)
    return WorkflowListResponse(items=items)


__all__ = ["get_workflow", "list_workflows"]
