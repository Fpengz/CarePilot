"""Domain policy evaluation for agent tool authorization decisions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, TypedDict, cast
from uuid import uuid4

from dietary_guardian.domain.identity.models import AccountRole
from dietary_guardian.domain.workflows.models import ToolPolicyEffect, ToolRolePolicyRecord


class ToolPolicyEvaluation(TypedDict):
    policy_mode: Literal["shadow", "enforce"]
    code_decision: Literal["allow", "deny"]
    db_decision: Literal["allow", "deny"] | None
    effective_decision: Literal["allow", "deny"]
    diverged: bool
    matched_policy_id: str | None


def create_tool_policy_record(
    *,
    role: AccountRole,
    agent_id: str,
    tool_name: str,
    effect: ToolPolicyEffect,
    conditions: dict[str, object] | None = None,
    priority: int = 0,
    enabled: bool = True,
) -> ToolRolePolicyRecord:
    now = datetime.now(timezone.utc)
    return ToolRolePolicyRecord(
        id=f"tp-{uuid4().hex}",
        role=role,
        agent_id=agent_id,
        tool_name=tool_name,
        effect=effect,
        conditions=conditions or {},
        priority=priority,
        enabled=enabled,
        created_at=now,
        updated_at=now,
    )


def apply_tool_policy_patch(record: ToolRolePolicyRecord, patch: dict[str, object]) -> ToolRolePolicyRecord:
    next_conditions = patch.get("conditions", record.conditions)
    if not isinstance(next_conditions, dict):
        next_conditions = record.conditions
    typed_conditions: dict[str, object] = cast(dict[str, object], next_conditions)
    raw_effect = patch.get("effect", record.effect)
    effect: ToolPolicyEffect = record.effect
    if raw_effect in {"allow", "deny"}:
        effect = cast(ToolPolicyEffect, raw_effect)
    raw_priority = patch.get("priority", record.priority)
    priority = record.priority
    if isinstance(raw_priority, int):
        priority = raw_priority
    raw_enabled = patch.get("enabled", record.enabled)
    enabled = record.enabled
    if isinstance(raw_enabled, bool):
        enabled = raw_enabled
    return ToolRolePolicyRecord(
        id=record.id,
        role=record.role,
        agent_id=record.agent_id,
        tool_name=record.tool_name,
        effect=effect,
        conditions=typed_conditions,
        priority=priority,
        enabled=enabled,
        created_at=record.created_at,
        updated_at=datetime.now(timezone.utc),
    )


def resolve_db_decision(
    *,
    policies: list[ToolRolePolicyRecord],
    role: str,
    agent_id: str,
    tool_name: str,
    environment: str,
) -> tuple[str | None, ToolRolePolicyRecord | None]:
    matches = [
        policy
        for policy in policies
        if policy.enabled
        and policy.role == role
        and policy.agent_id == agent_id
        and policy.tool_name == tool_name
        and _environment_match(policy=policy, environment=environment)
    ]
    if not matches:
        return None, None
    matches.sort(key=lambda item: (item.priority, 1 if item.effect == "deny" else 0, item.updated_at), reverse=True)
    top = matches[0]
    return top.effect, top


def evaluate_tool_policy(
    *,
    policies: list[ToolRolePolicyRecord],
    role: str,
    agent_id: str,
    tool_name: str,
    environment: str,
    code_allows_tool: bool,
    mode: Literal["shadow", "enforce"],
) -> ToolPolicyEvaluation:
    code_decision: Literal["allow", "deny"] = "allow" if code_allows_tool else "deny"
    db_decision, matched = resolve_db_decision(
        policies=policies,
        role=role,
        agent_id=agent_id,
        tool_name=tool_name,
        environment=environment,
    )
    typed_db_decision = cast(Literal["allow", "deny"] | None, db_decision)
    effective: Literal["allow", "deny"] = code_decision
    if mode == "enforce" and db_decision is not None:
        effective = cast(Literal["allow", "deny"], db_decision)
    payload: dict[str, Any] = {
        "policy_mode": mode,
        "code_decision": code_decision,
        "db_decision": typed_db_decision,
        "effective_decision": effective,
        "diverged": db_decision is not None and db_decision != code_decision,
        "matched_policy_id": matched.id if matched is not None else None,
    }
    return cast(ToolPolicyEvaluation, payload)


def _environment_match(*, policy: ToolRolePolicyRecord, environment: str) -> bool:
    raw = policy.conditions.get("environment")
    if raw is None:
        return True
    if isinstance(raw, str):
        return raw == environment
    if isinstance(raw, list):
        return environment in [str(item) for item in raw]
    return False
