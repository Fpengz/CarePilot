"""API orchestration entry points for companion, clinician digest, and impact views.

Shim: logic now lives in dietary_api._companion_orchestration.
"""

from __future__ import annotations

from dietary_api._companion_orchestration import (  # noqa: F401
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
