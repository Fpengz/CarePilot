from __future__ import annotations

from dataclasses import dataclass

from langgraph.graph import END, START, StateGraph

from care_pilot.features.workflows.trace_emitter import WorkflowTraceContext, WorkflowTraceEmitter
from care_pilot.platform.cache import EventTimelineService
from care_pilot.platform.observability.workflows.domain.models import (
    WorkflowExecutionResult,
    WorkflowName,
)
from care_pilot.platform.persistence import AppStores

from .prescription_ingest_output import PrescriptionIngestOutput
from .prescription_ingest_state import PrescriptionIngestState


@dataclass(frozen=True)
class PrescriptionIngestDeps:
    stores: AppStores
    event_timeline: EventTimelineService


@dataclass(slots=True)
class PrescriptionIngestGraphState:
    data: PrescriptionIngestState
    output: PrescriptionIngestOutput | None = None


def build_prescription_ingest_graph(*, deps: PrescriptionIngestDeps) -> StateGraph:
    async def start_node(state: PrescriptionIngestGraphState) -> dict[str, object]:
        data = state.data
        emitter = WorkflowTraceEmitter(deps.event_timeline)
        trace_ctx = WorkflowTraceContext(
            workflow_name=WorkflowName.PRESCRIPTION_INGEST.value,
            correlation_id=data.correlation_id,
            request_id=data.request_id,
            user_id=data.user_id,
        )
        emitter.workflow_started(
            trace_ctx,
            payload={"source": data.source},
        )
        return {}

    async def not_implemented_node(state: PrescriptionIngestGraphState) -> dict[str, object]:
        data = state.data
        emitter = WorkflowTraceEmitter(deps.event_timeline)
        trace_ctx = WorkflowTraceContext(
            workflow_name=WorkflowName.PRESCRIPTION_INGEST.value,
            correlation_id=data.correlation_id,
            request_id=data.request_id,
            user_id=data.user_id,
        )
        emitter.workflow_completed(
            trace_ctx,
            payload={"status": "not_implemented"},
        )
        workflow = WorkflowExecutionResult(
            workflow_name=WorkflowName.PRESCRIPTION_INGEST,
            request_id=data.request_id,
            correlation_id=data.correlation_id,
            user_id=data.user_id,
            timeline_events=deps.event_timeline.get_events(correlation_id=data.correlation_id),
        )
        output = PrescriptionIngestOutput(status="not_implemented", workflow=workflow)
        return {"output": output}

    workflow = StateGraph(PrescriptionIngestGraphState)
    workflow.add_node("start", start_node)
    workflow.add_node("not_implemented", not_implemented_node)

    workflow.add_edge(START, "start")
    workflow.add_edge("start", "not_implemented")
    workflow.add_edge("not_implemented", END)
    return workflow


async def run_prescription_ingest_workflow(
    *,
    deps: PrescriptionIngestDeps,
    state: PrescriptionIngestState,
) -> PrescriptionIngestOutput:
    graph = build_prescription_ingest_graph(deps=deps).compile()
    final_state = await graph.ainvoke(PrescriptionIngestGraphState(data=state))
    if isinstance(final_state, PrescriptionIngestGraphState):
        output = final_state.output
    elif isinstance(final_state, dict):
        output = final_state.get("output")
    else:
        output = None
    if output is None:
        raise ValueError("prescription ingest workflow did not produce output")
    return output
