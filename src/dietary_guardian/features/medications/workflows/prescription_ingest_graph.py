from __future__ import annotations

from dataclasses import dataclass

from pydantic_graph import BaseNode, End, Graph, GraphRunContext, SimpleStatePersistence

from dietary_guardian.features.workflows.trace_emitter import WorkflowTraceContext, WorkflowTraceEmitter
from dietary_guardian.platform.cache import EventTimelineService
from dietary_guardian.platform.observability.workflows.domain.models import WorkflowExecutionResult, WorkflowName
from dietary_guardian.platform.persistence import AppStores

from .prescription_ingest_output import PrescriptionIngestOutput
from .prescription_ingest_state import PrescriptionIngestState


@dataclass(frozen=True)
class PrescriptionIngestDeps:
    stores: AppStores
    event_timeline: EventTimelineService


class Start(BaseNode[PrescriptionIngestState, PrescriptionIngestDeps, PrescriptionIngestOutput]):
    async def run(
        self,
        ctx: GraphRunContext[PrescriptionIngestState, PrescriptionIngestDeps],
    ) -> BaseNode[PrescriptionIngestState, PrescriptionIngestDeps, PrescriptionIngestOutput] | End[PrescriptionIngestOutput]:
        emitter = WorkflowTraceEmitter(ctx.deps.event_timeline)
        trace_ctx = WorkflowTraceContext(
            workflow_name=WorkflowName.PRESCRIPTION_INGEST.value,
            correlation_id=ctx.state.correlation_id,
            request_id=ctx.state.request_id,
            user_id=ctx.state.user_id,
        )
        emitter.workflow_started(
            trace_ctx,
            payload={"source": ctx.state.source},
        )
        return NotImplementedYet()


class NotImplementedYet(BaseNode[PrescriptionIngestState, PrescriptionIngestDeps, PrescriptionIngestOutput]):
    async def run(
        self,
        ctx: GraphRunContext[PrescriptionIngestState, PrescriptionIngestDeps],
    ) -> BaseNode[PrescriptionIngestState, PrescriptionIngestDeps, PrescriptionIngestOutput] | End[PrescriptionIngestOutput]:
        emitter = WorkflowTraceEmitter(ctx.deps.event_timeline)
        trace_ctx = WorkflowTraceContext(
            workflow_name=WorkflowName.PRESCRIPTION_INGEST.value,
            correlation_id=ctx.state.correlation_id,
            request_id=ctx.state.request_id,
            user_id=ctx.state.user_id,
        )
        emitter.workflow_completed(
            trace_ctx,
            payload={"status": "not_implemented"},
        )
        workflow = WorkflowExecutionResult(
            workflow_name=WorkflowName.PRESCRIPTION_INGEST,
            request_id=ctx.state.request_id,
            correlation_id=ctx.state.correlation_id,
            user_id=ctx.state.user_id,
            timeline_events=ctx.deps.event_timeline.get_events(correlation_id=ctx.state.correlation_id),
        )
        return End(PrescriptionIngestOutput(status="not_implemented", workflow=workflow))


prescription_ingest_graph: Graph[PrescriptionIngestState, PrescriptionIngestDeps, PrescriptionIngestOutput] = Graph(
    nodes=[Start, NotImplementedYet],
    name="prescription_ingest",
    state_type=PrescriptionIngestState,
    run_end_type=PrescriptionIngestOutput,
)


async def run_prescription_ingest_workflow(
    *,
    deps: PrescriptionIngestDeps,
    state: PrescriptionIngestState,
) -> PrescriptionIngestOutput:
    persistence = SimpleStatePersistence()
    result = await prescription_ingest_graph.run(Start(), state=state, deps=deps, persistence=persistence)
    return result.output
