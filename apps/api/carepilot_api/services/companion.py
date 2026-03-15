"""
Expose companion orchestration entrypoints for API routes.

This module provides high-level functions for companion interactions,
clinician digest reads, and impact summary responses.
"""

from __future__ import annotations

from care_pilot.features.companion.core.use_cases import (  # noqa: F401
    build_companion_today_bundle as _build_companion_today_bundle,
    run_companion_interaction as _run_companion_interaction,
)
from care_pilot.features.companion.core.context_loader import (  # noqa: F401
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
