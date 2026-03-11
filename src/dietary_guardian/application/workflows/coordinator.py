"""Workflow orchestrator for meal, alert, report, and replay execution.

Consolidates support helpers, contract snapshot CRUD, execution functions,
and tool-policy management previously split across five service modules.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from dietary_guardian.application.meals import build_meal_analysis_output
from dietary_guardian.domain.alerts.models import AlertSeverity
from dietary_guardian.domain.identity.models import UserProfile
from dietary_guardian.domain.tooling import (
    apply_tool_policy_patch,
    create_tool_policy_record,
    evaluate_tool_policy,
)
from dietary_guardian.domain.tooling.models import ToolPolicyContext
from dietary_guardian.domain.workflows.models import (
    ToolRolePolicyRecord,
    WorkflowContractSnapshotRecord,
    WorkflowExecutionResult,
    WorkflowName,
    WorkflowTimelineEvent,
)
from dietary_guardian.infrastructure.cache import (
    ClinicalSnapshotMemoryService,
    EventTimelineService,
    ProfileMemoryService,
)
from dietary_guardian.infrastructure.observability import get_logger
from dietary_guardian.infrastructure.tooling.registry import ToolRegistry
from dietary_guardian.application.contracts.agent_envelopes import AgentHandoff, CaptureEnvelope
from dietary_guardian.domain.meals.models import VisionResult

if TYPE_CHECKING:
    from apps.api.dietary_api.deps import AppContext, WorkflowDeps
    from apps.api.dietary_api.schemas import (
        ToolPolicyCreateRequest,
        ToolPolicyEvaluationResponse,
        ToolPolicyItemResponse,
        ToolPolicyListResponse,
        ToolPolicyPatchRequest,
        ToolPolicyWriteResponse,
        WorkflowListItem,
        WorkflowListResponse,
        WorkflowResponse,
        WorkflowRuntimeRegistryResponse,
        WorkflowSnapshotCompareResponse,
        WorkflowSnapshotItemResponse,
        WorkflowSnapshotListResponse,
        WorkflowSnapshotWriteResponse,
        WorkflowTimelineEventResponse,
    )

logger = get_logger(__name__)

WORKFLOW_DEFINITIONS: dict[WorkflowName, list[str]] = {
    WorkflowName.MEAL_ANALYSIS: ["meal_analysis", "dietary_reasoning", "emit_timeline"],
    WorkflowName.ALERT_ONLY: ["tool_trigger_alert", "emit_timeline"],
    WorkflowName.REPORT_PARSE: ["parse_biomarkers", "summarize_symptoms", "emit_timeline"],
    WorkflowName.REPLAY: ["read_timeline"],
}


class WorkflowCoordinator:
    """Coordinates agent handoffs and durable workflow traces."""

    def __init__(self, *, tool_registry: ToolRegistry, profile_memory: ProfileMemoryService, clinical_memory: ClinicalSnapshotMemoryService, event_timeline: EventTimelineService) -> None:
        self.tool_registry = tool_registry
        self.profile_memory = profile_memory
        self.clinical_memory = clinical_memory
        self.event_timeline = event_timeline

    def run_meal_analysis_workflow(self, *, capture: CaptureEnvelope, vision_result: VisionResult, user_profile: UserProfile, meal_record_id: str | None = None) -> WorkflowExecutionResult:
        self.profile_memory.put(user_profile)
        self.event_timeline.append(
            event_type="workflow_started",
            workflow_name=WorkflowName.MEAL_ANALYSIS,
            correlation_id=capture.correlation_id,
            request_id=capture.request_id,
            user_id=user_profile.id,
            payload={"steps": WORKFLOW_DEFINITIONS[WorkflowName.MEAL_ANALYSIS], "capture_source": capture.source, "meal_filename": capture.filename, "mime_type": capture.mime_type},
        )
        output = build_meal_analysis_output(request_id=capture.request_id, correlation_id=capture.correlation_id, user_id=user_profile.id, profile_mode=user_profile.profile_mode, source=capture.source, vision_result=vision_result)
        handoffs = [AgentHandoff(from_agent="meal_analysis_agent", to_agent="dietary_agent", request_id=capture.request_id, correlation_id=capture.correlation_id, confidence=vision_result.primary_state.confidence_score, obligations=["evaluate_meal_against_clinical_snapshot"], payload={"dish_name": vision_result.primary_state.dish_name})]
        if vision_result.needs_manual_review:
            handoffs.append(AgentHandoff(from_agent="dietary_agent", to_agent="notification_agent", request_id=capture.request_id, correlation_id=capture.correlation_id, confidence=vision_result.primary_state.confidence_score, obligations=["request_clarification_from_patient"], payload={"reason": "manual_review_required"}))
        self.event_timeline.append(
            event_type="workflow_completed",
            workflow_name=WorkflowName.MEAL_ANALYSIS,
            correlation_id=capture.correlation_id,
            request_id=capture.request_id,
            user_id=user_profile.id,
            payload={"dish_name": vision_result.primary_state.dish_name, "manual_review": vision_result.needs_manual_review, "handoff_count": len(handoffs), "meal_record_id": meal_record_id, "confidence": vision_result.primary_state.confidence_score, "estimated_calories": vision_result.primary_state.nutrition.calories, "model_version": vision_result.model_version},
        )
        return WorkflowExecutionResult(workflow_name=WorkflowName.MEAL_ANALYSIS, request_id=capture.request_id, correlation_id=capture.correlation_id, user_id=user_profile.id, output_envelope=output, handoffs=handoffs, timeline_events=self.event_timeline.get_events(correlation_id=capture.correlation_id))

    def run_alert_workflow(self, *, user_profile: UserProfile, alert_type: str, severity: AlertSeverity, message: str, destinations: list[str], request_id: str | None = None, correlation_id: str | None = None, account_role: str = "member", scopes: list[str] | None = None, environment: str = "dev") -> WorkflowExecutionResult:
        issued_request_id = request_id or str(uuid4())
        issued_correlation_id = correlation_id or str(uuid4())
        self.profile_memory.put(user_profile)
        self.event_timeline.append(event_type="workflow_started", workflow_name=WorkflowName.ALERT_ONLY, correlation_id=issued_correlation_id, request_id=issued_request_id, user_id=user_profile.id, payload={"alert_type": alert_type, "destinations": destinations})
        tool_result = self.tool_registry.execute("trigger_alert", {"alert_type": alert_type, "severity": severity, "message": message, "destinations": destinations}, ToolPolicyContext(account_role=account_role, scopes=scopes or [], environment=environment, user_id=user_profile.id, correlation_id=issued_correlation_id))
        handoffs = [AgentHandoff(from_agent="care_orchestrator", to_agent="notification_agent", request_id=issued_request_id, correlation_id=issued_correlation_id, confidence=1.0 if tool_result.success else 0.0, obligations=["deliver_alert_via_channels"], payload={"alert_type": alert_type, "destinations": destinations})]
        self.event_timeline.append(event_type="workflow_completed", workflow_name=WorkflowName.ALERT_ONLY, correlation_id=issued_correlation_id, request_id=issued_request_id, user_id=user_profile.id, payload={"tool_success": tool_result.success, "tool_name": tool_result.tool_name})
        return WorkflowExecutionResult(workflow_name=WorkflowName.ALERT_ONLY, request_id=issued_request_id, correlation_id=issued_correlation_id, user_id=user_profile.id, handoffs=handoffs, tool_results=[tool_result], timeline_events=self.event_timeline.get_events(correlation_id=issued_correlation_id))

    def run_report_parse_workflow(self, *, user_id: str, request_id: str, correlation_id: str, source: str, reading_count: int, symptom_checkin_count: int, red_flag_count: int, window: dict[str, object]) -> WorkflowExecutionResult:
        self.event_timeline.append(event_type="workflow_started", workflow_name=WorkflowName.REPORT_PARSE, correlation_id=correlation_id, request_id=request_id, user_id=user_id, payload={"source": source, "steps": WORKFLOW_DEFINITIONS[WorkflowName.REPORT_PARSE]})
        self.event_timeline.append(event_type="workflow_completed", workflow_name=WorkflowName.REPORT_PARSE, correlation_id=correlation_id, request_id=request_id, user_id=user_id, payload={"reading_count": reading_count, "symptom_checkin_count": symptom_checkin_count, "red_flag_count": red_flag_count, "window": window})
        return WorkflowExecutionResult(workflow_name=WorkflowName.REPORT_PARSE, request_id=request_id, correlation_id=correlation_id, user_id=user_id, timeline_events=self.event_timeline.get_events(correlation_id=correlation_id))

    def replay_workflow(self, correlation_id: str) -> WorkflowExecutionResult:
        events = self.event_timeline.get_events(correlation_id=correlation_id)
        request_id = events[0].request_id if events else str(uuid4())
        user_id = events[0].user_id if events else None
        logger.info("workflow_replay correlation_id=%s events=%s side_effects=false", correlation_id, len(events))
        return WorkflowExecutionResult(workflow_name=WorkflowName.REPLAY, request_id=request_id or str(uuid4()), correlation_id=correlation_id, user_id=user_id, timeline_events=events, replayed=True)


__all__ = ["WORKFLOW_DEFINITIONS", "WorkflowCoordinator"]


# ---------------------------------------------------------------------------
# Support helpers (response projectors + hashing)
# ---------------------------------------------------------------------------

def policy_item_response(item: ToolRolePolicyRecord) -> ToolPolicyItemResponse:
    """Project a persisted tool policy into the API response model."""
    from apps.api.dietary_api.schemas import ToolPolicyItemResponse as _ToolPolicyItemResponse
    return _ToolPolicyItemResponse(
        id=item.id,
        role=item.role,
        agent_id=item.agent_id,
        tool_name=item.tool_name,
        effect=item.effect,
        conditions=dict(item.conditions),
        priority=item.priority,
        enabled=item.enabled,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def runtime_contract_hash(runtime: WorkflowRuntimeRegistryResponse) -> str:
    """Create a deterministic hash for the serialized workflow runtime contract."""
    normalized = json.dumps(runtime.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def snapshot_item_response(item: WorkflowContractSnapshotRecord) -> WorkflowSnapshotItemResponse:
    """Project a stored workflow contract snapshot into the API response model."""
    from apps.api.dietary_api.schemas import WorkflowSnapshotItemResponse as _WorkflowSnapshotItemResponse
    return _WorkflowSnapshotItemResponse(
        id=item.id,
        version=item.version,
        contract_hash=item.contract_hash,
        source=item.source,
        created_by=item.created_by,
        created_at=item.created_at,
    )


def timeline_event_response(event: WorkflowTimelineEvent) -> WorkflowTimelineEventResponse:
    """Project a workflow timeline event into the API response model."""
    from apps.api.dietary_api.schemas import (
        WorkflowTimelineEventPayloadResponse as _WorkflowTimelineEventPayloadResponse,
        WorkflowTimelineEventResponse as _WorkflowTimelineEventResponse,
    )
    payload = event.model_dump(mode="json")
    return _WorkflowTimelineEventResponse(
        event_id=str(payload["event_id"]),
        event_type=str(payload["event_type"]),
        workflow_name=str(payload["workflow_name"]) if payload.get("workflow_name") is not None else None,
        request_id=str(payload["request_id"]) if payload.get("request_id") is not None else None,
        correlation_id=str(payload["correlation_id"]),
        user_id=str(payload["user_id"]) if payload.get("user_id") is not None else None,
        payload=_WorkflowTimelineEventPayloadResponse.model_validate(dict(payload.get("payload") or {})),
        created_at=payload["created_at"],
    )


# ---------------------------------------------------------------------------
# Execution functions (workflow retrieval and listing)
# ---------------------------------------------------------------------------

def get_workflow(*, deps: WorkflowDeps, correlation_id: str) -> WorkflowResponse:
    """Replay a workflow timeline for a single correlation id."""
    from apps.api.dietary_api.schemas import WorkflowResponse as _WorkflowResponse
    workflow = deps.coordinator.replay_workflow(correlation_id)
    return _WorkflowResponse(
        workflow_name=str(workflow.workflow_name),
        request_id=workflow.request_id,
        correlation_id=workflow.correlation_id,
        replayed=workflow.replayed,
        timeline_events=[timeline_event_response(event) for event in workflow.timeline_events],
    )


def list_workflows(*, deps: WorkflowDeps) -> WorkflowListResponse:
    """List known workflows grouped by correlation id."""
    from apps.api.dietary_api.schemas import WorkflowListItem as _WorkflowListItem, WorkflowListResponse as _WorkflowListResponse
    events = deps.event_timeline.get_events()
    by_correlation: dict[str, WorkflowListItem] = {}
    for event in events:
        item = by_correlation.get(event.correlation_id)
        if item is None:
            item = _WorkflowListItem(
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
    return _WorkflowListResponse(items=items)


# ---------------------------------------------------------------------------
# Contract snapshot CRUD
# ---------------------------------------------------------------------------

def get_runtime_contract(*, deps: WorkflowDeps) -> WorkflowRuntimeRegistryResponse:
    """Expose the active workflow and agent runtime contract."""
    from apps.api.dietary_api.schemas import (
        AgentContractResponse as _AgentContractResponse,
        WorkflowRuntimeContractResponse as _WorkflowRuntimeContractResponse,
        WorkflowRuntimeRegistryResponse as _WorkflowRuntimeRegistryResponse,
        WorkflowRuntimeStepResponse as _WorkflowRuntimeStepResponse,
    )
    workflows = [
        _WorkflowRuntimeContractResponse(
            workflow_name=str(contract.workflow_name),
            steps=[
                _WorkflowRuntimeStepResponse(
                    step_id=step.step_id,
                    agent_id=step.agent_id,
                    capability=step.capability,
                    tool_names=list(step.tool_names),
                )
                for step in contract.steps
            ],
        )
        for contract in deps.agent_registry.list_workflow_contracts()
    ]
    agents = [
        _AgentContractResponse(
            agent_id=agent.agent_id,
            capabilities=list(agent.capabilities),
            allowed_tools=list(agent.allowed_tools),
            output_contract=agent.output_contract,
        )
        for agent in deps.agent_registry.list_agents()
    ]
    return _WorkflowRuntimeRegistryResponse(workflows=workflows, agents=agents)


def ensure_runtime_contract_snapshot_bootstrap(*, context: AppContext) -> WorkflowSnapshotWriteResponse | None:
    """Bootstrap the first workflow contract snapshot during startup when enabled."""
    from apps.api.dietary_api.deps import WorkflowDeps as _WorkflowDeps
    from apps.api.dietary_api.schemas import WorkflowSnapshotWriteResponse as _WorkflowSnapshotWriteResponse
    deps = _WorkflowDeps(
        settings=context.settings,
        stores=context.stores,
        event_timeline=context.event_timeline,
        agent_registry=context.agent_registry,
        coordinator=context.coordinator,
    )
    if not deps.settings.workers.workflow_contract_bootstrap:
        return None
    if not deps.stores.workflows.supports_contract_snapshots():
        return None
    runtime = get_runtime_contract(deps=deps)
    contract_hash = runtime_contract_hash(runtime)
    existing = deps.stores.workflows.list_workflow_contract_snapshots(limit=1)
    if existing and existing[0].contract_hash == contract_hash:
        return _WorkflowSnapshotWriteResponse(snapshot=snapshot_item_response(existing[0]))
    version = (existing[0].version + 1) if existing else 1
    snapshot = WorkflowContractSnapshotRecord(
        id=f"wcs-{uuid4().hex}",
        version=version,
        contract_hash=contract_hash,
        source="startup_bootstrap",
        workflows=deps.agent_registry.list_workflow_contracts(),
        agents=deps.agent_registry.list_agents(),
        created_by="system",
        created_at=datetime.now(timezone.utc),
    )
    saved = deps.stores.workflows.save_workflow_contract_snapshot(snapshot)
    return _WorkflowSnapshotWriteResponse(snapshot=snapshot_item_response(saved))


def list_runtime_contract_snapshots(*, deps: WorkflowDeps) -> WorkflowSnapshotListResponse:
    """List persisted workflow contract snapshots."""
    from apps.api.dietary_api.schemas import WorkflowSnapshotListResponse as _WorkflowSnapshotListResponse
    items = deps.stores.workflows.list_workflow_contract_snapshots()
    return _WorkflowSnapshotListResponse(items=[snapshot_item_response(item) for item in items])


def create_runtime_contract_snapshot(*, deps: WorkflowDeps, created_by: str | None) -> WorkflowSnapshotWriteResponse:
    """Persist a manual snapshot of the current workflow runtime contract."""
    from apps.api.dietary_api.schemas import WorkflowSnapshotWriteResponse as _WorkflowSnapshotWriteResponse
    runtime = get_runtime_contract(deps=deps)
    existing = deps.stores.workflows.list_workflow_contract_snapshots(limit=1)
    version = (existing[0].version + 1) if existing else 1
    snapshot = WorkflowContractSnapshotRecord(
        id=f"wcs-{uuid4().hex}",
        version=version,
        contract_hash=runtime_contract_hash(runtime),
        source="manual_api",
        workflows=deps.agent_registry.list_workflow_contracts(),
        agents=deps.agent_registry.list_agents(),
        created_by=created_by,
        created_at=datetime.now(timezone.utc),
    )
    saved = deps.stores.workflows.save_workflow_contract_snapshot(snapshot)
    return _WorkflowSnapshotWriteResponse(snapshot=snapshot_item_response(saved))


def compare_runtime_contract_snapshots(
    *,
    deps: WorkflowDeps,
    base_version: int,
    target_version: int,
) -> WorkflowSnapshotCompareResponse | None:
    """Compare two persisted workflow contract snapshots by version."""
    from apps.api.dietary_api.schemas import WorkflowSnapshotCompareResponse as _WorkflowSnapshotCompareResponse
    base = deps.stores.workflows.get_workflow_contract_snapshot(version=base_version)
    target = deps.stores.workflows.get_workflow_contract_snapshot(version=target_version)
    if base is None or target is None:
        return None
    changed = base.contract_hash != target.contract_hash
    return _WorkflowSnapshotCompareResponse(
        base_version=base.version,
        target_version=target.version,
        changed=changed,
        base_hash=base.contract_hash,
        target_hash=target.contract_hash,
    )


# ---------------------------------------------------------------------------
# Tool-policy management and evaluation
# ---------------------------------------------------------------------------

def list_tool_policies(*, deps: WorkflowDeps) -> ToolPolicyListResponse:
    """List stored tool-role policies."""
    from apps.api.dietary_api.schemas import ToolPolicyListResponse as _ToolPolicyListResponse
    items = deps.stores.workflows.list_tool_role_policies()
    return _ToolPolicyListResponse(items=[policy_item_response(item) for item in items])


def create_tool_policy(*, deps: WorkflowDeps, payload: ToolPolicyCreateRequest) -> ToolPolicyWriteResponse:
    """Create a persisted tool-role policy."""
    from apps.api.dietary_api.schemas import ToolPolicyWriteResponse as _ToolPolicyWriteResponse
    record = create_tool_policy_record(
        role=payload.role,
        agent_id=payload.agent_id,
        tool_name=payload.tool_name,
        effect=payload.effect,
        conditions=payload.conditions,
        priority=payload.priority,
        enabled=payload.enabled,
    )
    saved = deps.stores.workflows.save_tool_role_policy(record)
    return _ToolPolicyWriteResponse(policy=policy_item_response(saved))


def patch_tool_policy(*, deps: WorkflowDeps, policy_id: str, payload: ToolPolicyPatchRequest) -> ToolPolicyWriteResponse | None:
    """Apply a partial update to a stored tool-role policy."""
    from apps.api.dietary_api.schemas import ToolPolicyWriteResponse as _ToolPolicyWriteResponse
    current = deps.stores.workflows.get_tool_role_policy(policy_id)
    if current is None:
        return None
    patch = payload.model_dump(exclude_none=True)
    updated = apply_tool_policy_patch(current, patch)
    saved = deps.stores.workflows.save_tool_role_policy(updated)
    return _ToolPolicyWriteResponse(policy=policy_item_response(saved))


def evaluate_tool_policy_for_runtime(
    *,
    deps: WorkflowDeps,
    role: str,
    agent_id: str,
    tool_name: str,
    environment: str,
) -> ToolPolicyEvaluationResponse:
    """Evaluate the effective tool-policy decision for a runtime call."""
    from apps.api.dietary_api.schemas import ToolPolicyEvaluationResponse as _ToolPolicyEvaluationResponse
    agent = next((item for item in deps.agent_registry.list_agents() if item.agent_id == agent_id), None)
    code_allows_tool = agent is not None and tool_name in set(agent.allowed_tools)
    policies = deps.stores.workflows.list_tool_role_policies(
        role=role,
        agent_id=agent_id,
        tool_name=tool_name,
        enabled_only=True,
    )
    evaluation = evaluate_tool_policy(
        policies=policies,
        role=role,
        agent_id=agent_id,
        tool_name=tool_name,
        environment=environment,
        code_allows_tool=code_allows_tool,
        mode=deps.settings.workers.tool_policy_enforcement_mode,
    )
    return _ToolPolicyEvaluationResponse(
        policy_mode=evaluation["policy_mode"],
        code_decision=evaluation["code_decision"],
        db_decision=evaluation["db_decision"],
        effective_decision=evaluation["effective_decision"],
        diverged=evaluation["diverged"],
        matched_policy_id=evaluation["matched_policy_id"],
    )
