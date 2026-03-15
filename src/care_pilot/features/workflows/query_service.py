"""Feature-facing workflow trace query helpers.

Workflows are traced via `EventTimelineService` and queried by correlation id.
This module provides deterministic read helpers without imposing a central
workflow runtime abstraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from care_pilot.platform.cache import EventTimelineService
from care_pilot.platform.observability.workflows.domain.models import (
    WorkflowExecutionResult,
    WorkflowName,
    WorkflowTimelineEvent,
)


@dataclass(frozen=True, slots=True)
class WorkflowRunSummary:
    correlation_id: str
    request_id: str | None
    user_id: str | None
    workflow_name: str | None
    created_at: datetime
    latest_event_at: datetime
    event_count: int


def list_workflow_runs(
    *, event_timeline: EventTimelineService
) -> list[WorkflowRunSummary]:
    events = event_timeline.get_events()
    by_correlation: dict[str, WorkflowRunSummary] = {}
    for event in events:
        existing = by_correlation.get(event.correlation_id)
        if existing is None:
            by_correlation[event.correlation_id] = WorkflowRunSummary(
                correlation_id=event.correlation_id,
                request_id=event.request_id,
                user_id=event.user_id,
                workflow_name=event.workflow_name,
                created_at=event.created_at,
                latest_event_at=event.created_at,
                event_count=1,
            )
            continue
        latest = (
            event.created_at
            if event.created_at > existing.latest_event_at
            else existing.latest_event_at
        )
        by_correlation[event.correlation_id] = WorkflowRunSummary(
            correlation_id=existing.correlation_id,
            request_id=existing.request_id or event.request_id,
            user_id=existing.user_id or event.user_id,
            workflow_name=existing.workflow_name or event.workflow_name,
            created_at=existing.created_at,
            latest_event_at=latest,
            event_count=existing.event_count + 1,
        )
    return sorted(
        by_correlation.values(),
        key=lambda item: item.latest_event_at,
        reverse=True,
    )


def replay_workflow(
    *,
    event_timeline: EventTimelineService,
    correlation_id: str,
) -> WorkflowExecutionResult:
    events: list[WorkflowTimelineEvent] = event_timeline.get_events(
        correlation_id=correlation_id
    )
    request_id = events[0].request_id if events else str(uuid4())
    user_id = events[0].user_id if events else None
    return WorkflowExecutionResult(
        workflow_name=WorkflowName.REPLAY,
        request_id=request_id or str(uuid4()),
        correlation_id=correlation_id,
        user_id=user_id,
        timeline_events=events,
        replayed=True,
    )
