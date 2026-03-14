"""
Provide a compatibility shim for companion orchestration imports.

This module re-exports orchestration helpers so legacy imports continue to
resolve while API services are reorganized.
"""

from __future__ import annotations

from dietary_guardian.features.companion.core.context_loader import (  # noqa: F401
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
