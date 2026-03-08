from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..routes_shared import current_session, get_context, require_action
from ..schemas.workflows import (
    ToolPolicyCreateRequest,
    ToolPolicyEvaluationResponse,
    ToolPolicyListResponse,
    ToolPolicyPatchRequest,
    ToolPolicyWriteResponse,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowRuntimeRegistryResponse,
    WorkflowSnapshotCompareResponse,
    WorkflowSnapshotListResponse,
    WorkflowSnapshotWriteResponse,
)
from ..services.workflows import (
    compare_runtime_contract_snapshots,
    create_runtime_contract_snapshot,
    create_tool_policy,
    evaluate_tool_policy_for_runtime,
    get_runtime_contract,
    get_workflow,
    list_runtime_contract_snapshots,
    list_tool_policies,
    list_workflows,
    patch_tool_policy,
)

router = APIRouter(tags=["workflows"])


@router.get("/api/v1/workflows", response_model=WorkflowListResponse)
def workflows_list(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> WorkflowListResponse:
    require_action(session, "workflows.read")
    return list_workflows(context=get_context(request))


@router.get("/api/v1/workflows/runtime-contract", response_model=WorkflowRuntimeRegistryResponse)
def workflow_runtime_contract(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> WorkflowRuntimeRegistryResponse:
    require_action(session, "workflows.read")
    return get_runtime_contract(context=get_context(request))


@router.get("/api/v1/workflows/runtime-contract/snapshots", response_model=WorkflowSnapshotListResponse)
def workflow_runtime_contract_snapshots(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> WorkflowSnapshotListResponse:
    require_action(session, "workflows.read")
    return list_runtime_contract_snapshots(context=get_context(request))


@router.post("/api/v1/workflows/runtime-contract/snapshots", response_model=WorkflowSnapshotWriteResponse)
def workflow_runtime_contract_snapshot_create(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> WorkflowSnapshotWriteResponse:
    require_action(session, "workflows.write")
    created_by = str(session.get("user_id")) if session.get("user_id") is not None else None
    return create_runtime_contract_snapshot(context=get_context(request), created_by=created_by)


@router.get("/api/v1/workflows/runtime-contract/snapshots/compare", response_model=WorkflowSnapshotCompareResponse)
def workflow_runtime_contract_snapshot_compare(
    request: Request,
    base_version: int = Query(ge=1),
    target_version: int = Query(ge=1),
    session: dict[str, object] = Depends(current_session),
) -> WorkflowSnapshotCompareResponse:
    require_action(session, "workflows.read")
    comparison = compare_runtime_contract_snapshots(
        context=get_context(request),
        base_version=base_version,
        target_version=target_version,
    )
    if comparison is None:
        raise HTTPException(status_code=404, detail="snapshot not found")
    return comparison


@router.get("/api/v1/workflows/tool-policies", response_model=ToolPolicyListResponse)
def workflow_tool_policies_list(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ToolPolicyListResponse:
    require_action(session, "workflows.read")
    return list_tool_policies(context=get_context(request))


@router.post("/api/v1/workflows/tool-policies", response_model=ToolPolicyWriteResponse)
def workflow_tool_policies_create(
    payload: ToolPolicyCreateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ToolPolicyWriteResponse:
    require_action(session, "workflows.write")
    return create_tool_policy(context=get_context(request), payload=payload)


@router.patch("/api/v1/workflows/tool-policies/{policy_id}", response_model=ToolPolicyWriteResponse)
def workflow_tool_policies_patch(
    policy_id: str,
    payload: ToolPolicyPatchRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ToolPolicyWriteResponse:
    require_action(session, "workflows.write")
    updated = patch_tool_policy(context=get_context(request), policy_id=policy_id, payload=payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="policy not found")
    return updated


@router.get("/api/v1/workflows/tool-policies/evaluation", response_model=ToolPolicyEvaluationResponse)
def workflow_tool_policies_evaluation(
    request: Request,
    role: str,
    agent_id: str,
    tool_name: str,
    environment: str = "dev",
    session: dict[str, object] = Depends(current_session),
) -> ToolPolicyEvaluationResponse:
    require_action(session, "workflows.read")
    return evaluate_tool_policy_for_runtime(
        context=get_context(request),
        role=role,
        agent_id=agent_id,
        tool_name=tool_name,
        environment=environment,
    )


@router.get("/api/v1/workflows/{correlation_id}", response_model=WorkflowResponse)
def workflow_get(
    correlation_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> WorkflowResponse:
    require_action(session, "workflows.replay")
    return get_workflow(context=get_context(request), correlation_id=correlation_id)
