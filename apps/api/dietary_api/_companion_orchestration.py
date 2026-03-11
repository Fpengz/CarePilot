"""Compatibility shim for companion orchestration."""

from __future__ import annotations

from apps.api.dietary_api.services.companion_context import (  # noqa: F401
    build_workflow_response,
    get_clinician_digest,
    get_companion_today,
    get_impact_summary,
    handle_companion_interaction,
    load_companion_inputs,
)

__all__ = [
    "build_workflow_response",
    "get_clinician_digest",
    "get_companion_today",
    "get_impact_summary",
    "handle_companion_interaction",
    "load_companion_inputs",
]
