"""Workflow replay and listing operations for API endpoints.

.. deprecated::
    Thin re-export shim. All logic lives in
    ``dietary_guardian.application.workflows.coordinator``.
"""

from __future__ import annotations

from dietary_guardian.application.workflows.coordinator import (  # noqa: F401
    get_workflow,
    list_workflows,
)

__all__ = ["get_workflow", "list_workflows"]
