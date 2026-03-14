"""Workflow graph runner helpers.

This module is the intended home for `pydantic-graph` execution helpers.

Notes:
- Keep workflow logic in feature-owned `features/**/workflows/**`.
- Use `WorkflowTraceEmitter` to emit product-visible traces into
  `EventTimelineService`.
- LangGraph remains deferred until checkpointed/interruptible/long-lived flows
  become first-class requirements.
"""

from __future__ import annotations

from typing import Any, TypeVar

from dietary_guardian.features.workflows.trace_emitter import WorkflowTraceContext, WorkflowTraceEmitter

TState = TypeVar("TState")
TResult = TypeVar("TResult")


async def run_graph(
    *,
    workflow_name: str,
    correlation_id: str,
    request_id: str | None,
    user_id: str | None,
    graph: Any,
    state: TState,
    deps: Any,
    emitter: WorkflowTraceEmitter,
    payload_started: dict[str, object] | None = None,
) -> tuple[TState, Any]:
    """Run a pydantic-graph graph with best-effort trace emission.

    This helper intentionally avoids imposing a new central coordinator.
    """
    ctx = WorkflowTraceContext(
        workflow_name=workflow_name,
        correlation_id=correlation_id,
        request_id=request_id,
        user_id=user_id,
    )
    timer = emitter.step_timer()
    emitter.workflow_started(ctx, payload=payload_started)
    try:
        if hasattr(graph, "run") and callable(getattr(graph, "run")):
            result = await graph.run(state, deps=deps)
            emitter.workflow_completed(ctx, payload={"result_type": type(result).__name__}, duration_ms=timer.elapsed_ms())
            return state, result
        raise TypeError(f"Unsupported graph object: missing async run(): {type(graph)!r}")
    except Exception as exc:
        emitter.workflow_failed(
            ctx,
            error_code="workflow.graph_failed",
            message=str(exc),
            details={"exception_type": type(exc).__name__},
            duration_ms=timer.elapsed_ms(),
        )
        raise
