"""Workflow runtime-contract and snapshot operations for governance endpoints.

.. deprecated::
    Thin re-export shim. All logic lives in
    ``dietary_guardian.application.workflows.coordinator``.
"""

from __future__ import annotations

from dietary_guardian.application.workflows.coordinator import (  # noqa: F401
    compare_runtime_contract_snapshots,
    create_runtime_contract_snapshot,
    ensure_runtime_contract_snapshot_bootstrap,
    get_runtime_contract,
    list_runtime_contract_snapshots,
)

__all__ = [
    "compare_runtime_contract_snapshots",
    "create_runtime_contract_snapshot",
    "ensure_runtime_contract_snapshot_bootstrap",
    "get_runtime_contract",
    "list_runtime_contract_snapshots",
]
