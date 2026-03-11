"""Companion feature entrypoint.

Keep this module small: it should remain an obvious "start here" location.
Companion submodules live under `features.companion.*`.
"""

from __future__ import annotations

from dietary_guardian.features.companion.core.service import (  # noqa: F401
    CompanionRuntimeState,
    CompanionStateInputs,
    build_companion_today_bundle,
    build_companion_runtime_state,
    run_companion_interaction,
)

__all__ = [
    "CompanionRuntimeState",
    "CompanionStateInputs",
    "build_companion_today_bundle",
    "build_companion_runtime_state",
    "run_companion_interaction",
]

