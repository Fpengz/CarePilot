"""Workflow event timeline service.

Records ``WorkflowTimelineEvent`` objects in memory and optionally persists
them via a ``WorkflowTimelineRepository``.  Used by the workflow orchestrator
to trace multi-step execution for debugging and observability.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from dietary_guardian.domain.workflows.models import WorkflowTimelineEvent
from dietary_guardian.logging_config import get_logger

logger = get_logger(__name__)


class WorkflowTimelineRepository(Protocol):
    def save_workflow_timeline_event(self, event: WorkflowTimelineEvent) -> WorkflowTimelineEvent: ...

    def list_workflow_timeline_events(
        self,
        *,
        correlation_id: str | None = None,
        user_id: str | None = None,
    ) -> list[WorkflowTimelineEvent]: ...


class EventTimelineService:
    """Append-only event timeline with optional durable persistence."""

    def __init__(
        self,
        *,
        repository: WorkflowTimelineRepository | None = None,
        persistence_enabled: bool = False,
    ) -> None:
        self._events: list[WorkflowTimelineEvent] = []
        self._repository = repository
        self._persistence_enabled = persistence_enabled and repository is not None

    def append(
        self,
        *,
        event_type: str,
        correlation_id: str,
        payload: dict[str, object],
        request_id: str | None = None,
        user_id: str | None = None,
        workflow_name: str | None = None,
    ) -> WorkflowTimelineEvent:
        event = WorkflowTimelineEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            workflow_name=workflow_name,
            request_id=request_id,
            correlation_id=correlation_id,
            user_id=user_id,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )
        self._events.append(event)
        if self._persistence_enabled and self._repository is not None:
            self._repository.save_workflow_timeline_event(event)
        logger.info(
            "event_timeline_append event_type=%s workflow=%s correlation_id=%s request_id=%s",
            event.event_type,
            event.workflow_name,
            event.correlation_id,
            event.request_id,
        )
        return event

    def list(self, *, correlation_id: str | None = None, user_id: str | None = None) -> list[WorkflowTimelineEvent]:
        if self._persistence_enabled and self._repository is not None:
            return self._repository.list_workflow_timeline_events(
                correlation_id=correlation_id,
                user_id=user_id,
            )

        events = self._events
        if correlation_id is not None:
            events = [e for e in events if e.correlation_id == correlation_id]
        if user_id is not None:
            events = [e for e in events if e.user_id == user_id]
        return sorted(events, key=lambda e: e.created_at)


__all__ = ["EventTimelineService", "WorkflowTimelineRepository"]
