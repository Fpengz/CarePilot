"""Public workflow API service facade.

Thin re-export shim. Most logic lives in
``dietary_guardian.application.workflows.coordinator``.
get_workflow / list_workflows re-declared here so get_type_hints() resolves
WorkflowDeps at runtime (coordinator uses TYPE_CHECKING to avoid a cycle).
"""

from __future__ import annotations

from typing import Any

from apps.api.dietary_api.deps import WorkflowDeps
from dietary_guardian.application.workflows.coordinator import (  # noqa: F401
    compare_runtime_contract_snapshots,
    create_runtime_contract_snapshot,
    create_tool_policy,
    ensure_runtime_contract_snapshot_bootstrap,
    evaluate_tool_policy_for_runtime,
    get_runtime_contract,
    get_workflow as _get_workflow,
    list_runtime_contract_snapshots,
    list_tool_policies,
    list_workflows as _list_workflows,
    patch_tool_policy,
)


# Thin wrappers re-annotate deps so get_type_hints() resolves WorkflowDeps at runtime.
# coordinator.py hides WorkflowDeps under TYPE_CHECKING to avoid an import cycle.
def get_workflow(*, deps: WorkflowDeps, correlation_id: str) -> Any:
    return _get_workflow(deps=deps, correlation_id=correlation_id)


def list_workflows(*, deps: WorkflowDeps) -> Any:
    return _list_workflows(deps=deps)


__all__ = [
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
]
