"""Shared context-building helpers for companion API endpoints.

Shim: logic now lives in dietary_api._companion_orchestration.
"""

from __future__ import annotations

from dietary_api._companion_orchestration import (  # noqa: F401
    build_workflow_response,
    load_companion_inputs,
)

__all__ = ["build_workflow_response", "load_companion_inputs"]
