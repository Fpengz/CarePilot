from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.schemas import WorkflowListItem, WorkflowListResponse, WorkflowResponse


def get_workflow(*, context: AppContext, correlation_id: str) -> WorkflowResponse:
    workflow = context.coordinator.replay_workflow(correlation_id)
    data = workflow.model_dump(mode="json")
    return WorkflowResponse(
        workflow_name=str(data["workflow_name"]),
        request_id=str(data["request_id"]),
        correlation_id=str(data["correlation_id"]),
        replayed=bool(data["replayed"]),
        timeline_events=[dict(event) for event in data["timeline_events"]],
    )


def list_workflows(*, context: AppContext) -> WorkflowListResponse:
    events = context.event_timeline.list()
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
    items = sorted(
        by_correlation.values(),
        key=lambda row: row.latest_event_at,
        reverse=True,
    )
    return WorkflowListResponse(items=items)
