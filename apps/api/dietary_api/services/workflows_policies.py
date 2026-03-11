"""Tool-policy management and evaluation for workflow governance endpoints.

.. deprecated::
    Thin re-export shim. All logic lives in
    ``dietary_guardian.application.workflows.coordinator``.
"""

from __future__ import annotations

from dietary_guardian.application.workflows.coordinator import (  # noqa: F401
    create_tool_policy,
    evaluate_tool_policy_for_runtime,
    list_tool_policies,
    patch_tool_policy,
)

__all__ = [
    "create_tool_policy",
    "evaluate_tool_policy_for_runtime",
    "list_tool_policies",
    "patch_tool_policy",
]
