"""Shared context-building helpers for companion API endpoints.

Shim: business logic lives in dietary_guardian.application.companion.context.
"""

from __future__ import annotations

from dietary_guardian.application.companion.context import (  # noqa: F401
    build_workflow_response,
    load_companion_inputs,
)

__all__ = ["build_workflow_response", "load_companion_inputs"]
