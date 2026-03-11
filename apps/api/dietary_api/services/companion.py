"""API orchestration entry points for companion, clinician digest, and impact views."""

from __future__ import annotations

from dietary_guardian.features.companion.core.use_cases import (  # noqa: F401
    build_companion_today_bundle as _build_companion_today_bundle,
    run_companion_interaction as _run_companion_interaction,
)
from apps.api.dietary_api.services.companion_context import (  # noqa: F401
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
