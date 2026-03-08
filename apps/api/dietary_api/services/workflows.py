import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.schemas import (
    AgentContractResponse,
    ToolPolicyCreateRequest,
    ToolPolicyEvaluationResponse,
    ToolPolicyItemResponse,
    ToolPolicyListResponse,
    ToolPolicyPatchRequest,
    ToolPolicyWriteResponse,
    WorkflowListItem,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowSnapshotCompareResponse,
    WorkflowSnapshotItemResponse,
    WorkflowSnapshotListResponse,
    WorkflowSnapshotWriteResponse,
    WorkflowTimelineEventResponse,
    WorkflowRuntimeContractResponse,
    WorkflowRuntimeRegistryResponse,
    WorkflowRuntimeStepResponse,
)
from dietary_guardian.models.tool_policy import ToolRolePolicyRecord
from dietary_guardian.models.workflow import WorkflowTimelineEvent
from dietary_guardian.models.workflow_contract_snapshot import WorkflowContractSnapshotRecord
from dietary_guardian.services.policy_service import apply_tool_policy_patch, create_tool_policy_record, evaluate_tool_policy


def get_workflow(*, context: AppContext, correlation_id: str) -> WorkflowResponse:
    workflow = context.coordinator.replay_workflow(correlation_id)
    return WorkflowResponse(
        workflow_name=str(workflow.workflow_name),
        request_id=workflow.request_id,
        correlation_id=workflow.correlation_id,
        replayed=workflow.replayed,
        timeline_events=[_timeline_event_response(event) for event in workflow.timeline_events],
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


def get_runtime_contract(*, context: AppContext) -> WorkflowRuntimeRegistryResponse:
    workflows = [
        WorkflowRuntimeContractResponse(
            workflow_name=str(contract.workflow_name),
            steps=[
                WorkflowRuntimeStepResponse(
                    step_id=step.step_id,
                    agent_id=step.agent_id,
                    capability=step.capability,
                    tool_names=list(step.tool_names),
                )
                for step in contract.steps
            ],
        )
        for contract in context.agent_registry.list_workflow_contracts()
    ]
    agents = [
        AgentContractResponse(
            agent_id=agent.agent_id,
            capabilities=list(agent.capabilities),
            allowed_tools=list(agent.allowed_tools),
            output_contract=agent.output_contract,
        )
        for agent in context.agent_registry.list_agents()
    ]
    return WorkflowRuntimeRegistryResponse(workflows=workflows, agents=agents)


def list_tool_policies(*, context: AppContext) -> ToolPolicyListResponse:
    items = context.stores.workflows.list_tool_role_policies()
    return ToolPolicyListResponse(items=[_policy_item_response(item) for item in items])


def create_tool_policy(*, context: AppContext, payload: ToolPolicyCreateRequest) -> ToolPolicyWriteResponse:
    record = create_tool_policy_record(
        role=payload.role,
        agent_id=payload.agent_id,
        tool_name=payload.tool_name,
        effect=payload.effect,
        conditions=payload.conditions,
        priority=payload.priority,
        enabled=payload.enabled,
    )
    saved = context.stores.workflows.save_tool_role_policy(record)
    return ToolPolicyWriteResponse(policy=_policy_item_response(saved))


def patch_tool_policy(*, context: AppContext, policy_id: str, payload: ToolPolicyPatchRequest) -> ToolPolicyWriteResponse | None:
    current = context.stores.workflows.get_tool_role_policy(policy_id)
    if current is None:
        return None
    patch = payload.model_dump(exclude_none=True)
    updated = apply_tool_policy_patch(current, patch)
    saved = context.stores.workflows.save_tool_role_policy(updated)
    return ToolPolicyWriteResponse(policy=_policy_item_response(saved))


def evaluate_tool_policy_for_runtime(
    *,
    context: AppContext,
    role: str,
    agent_id: str,
    tool_name: str,
    environment: str,
) -> ToolPolicyEvaluationResponse:
    agent = next((item for item in context.agent_registry.list_agents() if item.agent_id == agent_id), None)
    code_allows_tool = agent is not None and tool_name in set(agent.allowed_tools)
    policies = context.stores.workflows.list_tool_role_policies(
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
        mode=context.settings.tool_policy_enforcement_mode,
    )
    return ToolPolicyEvaluationResponse(
        policy_mode=evaluation["policy_mode"],
        code_decision=evaluation["code_decision"],
        db_decision=evaluation["db_decision"],
        effective_decision=evaluation["effective_decision"],
        diverged=evaluation["diverged"],
        matched_policy_id=evaluation["matched_policy_id"],
    )


def ensure_runtime_contract_snapshot_bootstrap(*, context: AppContext) -> WorkflowSnapshotWriteResponse | None:
    if not context.settings.workflow_contract_bootstrap:
        return None
    if not context.stores.workflows.supports_contract_snapshots():
        return None
    runtime = get_runtime_contract(context=context)
    contract_hash = _runtime_contract_hash(runtime)
    existing = context.stores.workflows.list_workflow_contract_snapshots(limit=1)
    if existing and existing[0].contract_hash == contract_hash:
        return WorkflowSnapshotWriteResponse(snapshot=_snapshot_item_response(existing[0]))
    version = (existing[0].version + 1) if existing else 1
    snapshot = WorkflowContractSnapshotRecord(
        id=f"wcs-{uuid4().hex}",
        version=version,
        contract_hash=contract_hash,
        source="startup_bootstrap",
        workflows=context.agent_registry.list_workflow_contracts(),
        agents=context.agent_registry.list_agents(),
        created_by="system",
        created_at=datetime.now(timezone.utc),
    )
    saved = context.stores.workflows.save_workflow_contract_snapshot(snapshot)
    return WorkflowSnapshotWriteResponse(snapshot=_snapshot_item_response(saved))


def list_runtime_contract_snapshots(*, context: AppContext) -> WorkflowSnapshotListResponse:
    items = context.stores.workflows.list_workflow_contract_snapshots()
    return WorkflowSnapshotListResponse(items=[_snapshot_item_response(item) for item in items])


def create_runtime_contract_snapshot(*, context: AppContext, created_by: str | None) -> WorkflowSnapshotWriteResponse:
    runtime = get_runtime_contract(context=context)
    existing = context.stores.workflows.list_workflow_contract_snapshots(limit=1)
    version = (existing[0].version + 1) if existing else 1
    snapshot = WorkflowContractSnapshotRecord(
        id=f"wcs-{uuid4().hex}",
        version=version,
        contract_hash=_runtime_contract_hash(runtime),
        source="manual_api",
        workflows=context.agent_registry.list_workflow_contracts(),
        agents=context.agent_registry.list_agents(),
        created_by=created_by,
        created_at=datetime.now(timezone.utc),
    )
    saved = context.stores.workflows.save_workflow_contract_snapshot(snapshot)
    return WorkflowSnapshotWriteResponse(snapshot=_snapshot_item_response(saved))


def compare_runtime_contract_snapshots(
    *,
    context: AppContext,
    base_version: int,
    target_version: int,
) -> WorkflowSnapshotCompareResponse | None:
    base = context.stores.workflows.get_workflow_contract_snapshot(version=base_version)
    target = context.stores.workflows.get_workflow_contract_snapshot(version=target_version)
    if base is None or target is None:
        return None
    changed = base.contract_hash != target.contract_hash
    return WorkflowSnapshotCompareResponse(
        base_version=base.version,
        target_version=target.version,
        changed=changed,
        base_hash=base.contract_hash,
        target_hash=target.contract_hash,
    )


def _policy_item_response(item: ToolRolePolicyRecord) -> ToolPolicyItemResponse:
    return ToolPolicyItemResponse(
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


def _runtime_contract_hash(runtime: WorkflowRuntimeRegistryResponse) -> str:
    normalized = json.dumps(runtime.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _snapshot_item_response(item: WorkflowContractSnapshotRecord) -> WorkflowSnapshotItemResponse:
    return WorkflowSnapshotItemResponse(
        id=item.id,
        version=item.version,
        contract_hash=item.contract_hash,
        source=item.source,
        created_by=item.created_by,
        created_at=item.created_at,
    )


def _timeline_event_response(event: WorkflowTimelineEvent) -> WorkflowTimelineEventResponse:
    payload = event.model_dump(mode="json")
    return WorkflowTimelineEventResponse(
        event_id=str(payload["event_id"]),
        event_type=str(payload["event_type"]),
        workflow_name=str(payload["workflow_name"]) if payload.get("workflow_name") is not None else None,
        request_id=str(payload["request_id"]) if payload.get("request_id") is not None else None,
        correlation_id=str(payload["correlation_id"]),
        user_id=str(payload["user_id"]) if payload.get("user_id") is not None else None,
        payload=dict(payload.get("payload") or {}),
        created_at=payload["created_at"],
    )
