"""
Expose companion orchestration entrypoints for API routes.

This module provides high-level functions for companion interactions,
clinician digest reads, and impact summary responses.
"""

from __future__ import annotations

from .companion_orchestration import (
    get_clinician_digest,
    get_companion_today,
    get_impact_summary,
    handle_companion_interaction as run_companion_interaction,
)

__all__ = [
    "get_clinician_digest",
    "get_companion_today",
    "get_impact_summary",
    "run_companion_interaction",
]
