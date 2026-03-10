"""Tool-policy management and evaluation for workflow governance endpoints."""

from __future__ import annotations

from apps.api.dietary_api.deps import WorkflowDeps
from apps.api.dietary_api.schemas import (
    ToolPolicyCreateRequest,
    ToolPolicyEvaluationResponse,
    ToolPolicyListResponse,
    ToolPolicyPatchRequest,
    ToolPolicyWriteResponse,
)
from apps.api.dietary_api.services.workflows_support import policy_item_response
from dietary_guardian.domain.tooling import (
    apply_tool_policy_patch,
    create_tool_policy_record,
    evaluate_tool_policy,
)


def list_tool_policies(*, deps: WorkflowDeps) -> ToolPolicyListResponse:
    """List stored tool-role policies."""
    items = deps.stores.workflows.list_tool_role_policies()
    return ToolPolicyListResponse(items=[policy_item_response(item) for item in items])



def create_tool_policy(*, deps: WorkflowDeps, payload: ToolPolicyCreateRequest) -> ToolPolicyWriteResponse:
    """Create a persisted tool-role policy."""
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
    return ToolPolicyWriteResponse(policy=policy_item_response(saved))



def patch_tool_policy(*, deps: WorkflowDeps, policy_id: str, payload: ToolPolicyPatchRequest) -> ToolPolicyWriteResponse | None:
    """Apply a partial update to a stored tool-role policy."""
    current = deps.stores.workflows.get_tool_role_policy(policy_id)
    if current is None:
        return None
    patch = payload.model_dump(exclude_none=True)
    updated = apply_tool_policy_patch(current, patch)
    saved = deps.stores.workflows.save_tool_role_policy(updated)
    return ToolPolicyWriteResponse(policy=policy_item_response(saved))



def evaluate_tool_policy_for_runtime(
    *,
    deps: WorkflowDeps,
    role: str,
    agent_id: str,
    tool_name: str,
    environment: str,
) -> ToolPolicyEvaluationResponse:
    """Evaluate the effective tool-policy decision for a runtime call."""
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
    return ToolPolicyEvaluationResponse(
        policy_mode=evaluation["policy_mode"],
        code_decision=evaluation["code_decision"],
        db_decision=evaluation["db_decision"],
        effective_decision=evaluation["effective_decision"],
        diverged=evaluation["diverged"],
        matched_policy_id=evaluation["matched_policy_id"],
    )


__all__ = [
    "create_tool_policy",
    "evaluate_tool_policy_for_runtime",
    "list_tool_policies",
    "patch_tool_policy",
]
