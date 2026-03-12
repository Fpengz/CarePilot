"""Canonical workflow coordinators for companion interactions."""

from __future__ import annotations

from typing import Any

__all__ = [
    "WORKFLOW_DEFINITIONS",
    "WorkflowCoordinator",
    "compare_runtime_contract_snapshots",
    "create_runtime_contract_snapshot",
    "create_tool_policy",
    "ensure_runtime_contract_snapshot_bootstrap",
    "evaluate_tool_policy_for_runtime",
    "get_runtime_contract",
    "get_workflow",
    "list_runtime_contract_snapshots",
    "list_tool_policies",
    "list_workflows",
    "patch_tool_policy",
    "policy_item_response",
    "runtime_contract_hash",
    "snapshot_item_response",
    "timeline_event_response",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from dietary_guardian.platform.observability.workflows import coordinator

    return getattr(coordinator, name)
