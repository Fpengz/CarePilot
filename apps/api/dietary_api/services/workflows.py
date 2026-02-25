from typing import cast

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.schemas import WorkflowListResponse, WorkflowResponse


def get_workflow(*, context: AppContext, correlation_id: str) -> WorkflowResponse:
    workflow = context.coordinator.replay_workflow(correlation_id)
    data = workflow.model_dump(mode="json")
    return WorkflowResponse(
        workflow_name=str(data["workflow_name"]),
        request_id=str(data["request_id"]),
        correlation_id=str(data["correlation_id"]),
        replayed=bool(data["replayed"]),
        timeline_events=cast(list[dict[str, object]], data["timeline_events"]),
    )


def list_workflows(*, context: AppContext) -> WorkflowListResponse:
    events = context.event_timeline.list()
    by_correlation: dict[str, dict[str, object]] = {}
    for event in events:
        item = by_correlation.setdefault(
            event.correlation_id,
            {
                "correlation_id": event.correlation_id,
                "request_id": event.request_id,
                "user_id": event.user_id,
                "workflow_name": event.workflow_name,
                "created_at": event.created_at.isoformat(),
                "latest_event_at": event.created_at.isoformat(),
                "event_count": 0,
            },
        )
        event_count = cast(int, item["event_count"])
        item["event_count"] = event_count + 1
        if event.workflow_name and not item.get("workflow_name"):
            item["workflow_name"] = event.workflow_name
        latest = str(item["latest_event_at"])
        current = event.created_at.isoformat()
        if current > latest:
            item["latest_event_at"] = current
    items = sorted(by_correlation.values(), key=lambda row: str(row["latest_event_at"]), reverse=True)
    return WorkflowListResponse(items=cast(list[dict[str, object]], items))
