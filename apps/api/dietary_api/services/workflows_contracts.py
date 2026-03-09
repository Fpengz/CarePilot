"""Workflow runtime-contract and snapshot operations for governance endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from apps.api.dietary_api.deps import AppContext, WorkflowDeps
from apps.api.dietary_api.schemas import (
    AgentContractResponse,
    WorkflowRuntimeContractResponse,
    WorkflowRuntimeRegistryResponse,
    WorkflowRuntimeStepResponse,
    WorkflowSnapshotCompareResponse,
    WorkflowSnapshotListResponse,
    WorkflowSnapshotWriteResponse,
)
from apps.api.dietary_api.services.workflows_support import runtime_contract_hash, snapshot_item_response
from dietary_guardian.models.workflow_contract_snapshot import WorkflowContractSnapshotRecord


def get_runtime_contract(*, deps: WorkflowDeps) -> WorkflowRuntimeRegistryResponse:
    """Expose the active workflow and agent runtime contract."""
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
        for contract in deps.agent_registry.list_workflow_contracts()
    ]
    agents = [
        AgentContractResponse(
            agent_id=agent.agent_id,
            capabilities=list(agent.capabilities),
            allowed_tools=list(agent.allowed_tools),
            output_contract=agent.output_contract,
        )
        for agent in deps.agent_registry.list_agents()
    ]
    return WorkflowRuntimeRegistryResponse(workflows=workflows, agents=agents)



def ensure_runtime_contract_snapshot_bootstrap(*, context: AppContext) -> WorkflowSnapshotWriteResponse | None:
    """Bootstrap the first workflow contract snapshot during startup when enabled."""
    deps = WorkflowDeps(
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
        return WorkflowSnapshotWriteResponse(snapshot=snapshot_item_response(existing[0]))
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
    return WorkflowSnapshotWriteResponse(snapshot=snapshot_item_response(saved))



def list_runtime_contract_snapshots(*, deps: WorkflowDeps) -> WorkflowSnapshotListResponse:
    """List persisted workflow contract snapshots."""
    items = deps.stores.workflows.list_workflow_contract_snapshots()
    return WorkflowSnapshotListResponse(items=[snapshot_item_response(item) for item in items])



def create_runtime_contract_snapshot(*, deps: WorkflowDeps, created_by: str | None) -> WorkflowSnapshotWriteResponse:
    """Persist a manual snapshot of the current workflow runtime contract."""
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
    return WorkflowSnapshotWriteResponse(snapshot=snapshot_item_response(saved))



def compare_runtime_contract_snapshots(
    *,
    deps: WorkflowDeps,
    base_version: int,
    target_version: int,
) -> WorkflowSnapshotCompareResponse | None:
    """Compare two persisted workflow contract snapshots by version."""
    base = deps.stores.workflows.get_workflow_contract_snapshot(version=base_version)
    target = deps.stores.workflows.get_workflow_contract_snapshot(version=target_version)
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


__all__ = [
    "compare_runtime_contract_snapshots",
    "create_runtime_contract_snapshot",
    "ensure_runtime_contract_snapshot_bootstrap",
    "get_runtime_contract",
    "list_runtime_contract_snapshots",
]
