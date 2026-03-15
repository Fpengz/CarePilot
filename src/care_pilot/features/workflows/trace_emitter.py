"""Thin workflow trace emitter.

This is the preferred way for feature workflows to emit product-visible events
into the canonical trace sink (`EventTimelineService`).
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from care_pilot.platform.cache import EventTimelineService


@dataclass(frozen=True, slots=True)
class WorkflowTraceContext:
    workflow_name: str
    correlation_id: str
    request_id: str | None
    user_id: str | None


class WorkflowTraceEmitter:
    def __init__(self, event_timeline: EventTimelineService) -> None:
        self._event_timeline = event_timeline

    def workflow_started(
        self,
        ctx: WorkflowTraceContext,
        *,
        payload: dict[str, object] | None = None,
    ) -> None:
        self._event_timeline.append(
            event_type="workflow_started",
            workflow_name=ctx.workflow_name,
            correlation_id=ctx.correlation_id,
            request_id=ctx.request_id,
            user_id=ctx.user_id,
            payload=dict(payload or {}),
        )

    def workflow_completed(
        self,
        ctx: WorkflowTraceContext,
        *,
        payload: dict[str, object] | None = None,
        duration_ms: float | None = None,
    ) -> None:
        enriched: dict[str, object] = dict(payload or {})
        if duration_ms is not None:
            enriched["duration_ms"] = duration_ms
        self._event_timeline.append(
            event_type="workflow_completed",
            workflow_name=ctx.workflow_name,
            correlation_id=ctx.correlation_id,
            request_id=ctx.request_id,
            user_id=ctx.user_id,
            payload=enriched,
        )

    def workflow_failed(
        self,
        ctx: WorkflowTraceContext,
        *,
        error_code: str,
        message: str,
        details: dict[str, object] | None = None,
        duration_ms: float | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "error_code": error_code,
            "message": message,
            "details": dict(details or {}),
        }
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms
        self._event_timeline.append(
            event_type="workflow_failed",
            workflow_name=ctx.workflow_name,
            correlation_id=ctx.correlation_id,
            request_id=ctx.request_id,
            user_id=ctx.user_id,
            payload=payload,
        )

    def step_timer(self) -> "WorkflowStepTimer":
        return WorkflowStepTimer()


class WorkflowStepTimer:
    def __init__(self) -> None:
        self._started = perf_counter()

    def elapsed_ms(self) -> float:
        return (perf_counter() - self._started) * 1000
