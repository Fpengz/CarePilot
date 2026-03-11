"""Canonical companion-core service entrypoint."""

from __future__ import annotations

from dietary_guardian.features.companion.core.use_cases import (
    CompanionRuntimeState,
    CompanionStateInputs,
    build_companion_runtime_state,
    build_companion_today_bundle,
    run_companion_interaction,
)
__all__ = [
    "CompanionRuntimeState",
    "CompanionStateInputs",
    "build_companion_runtime_state",
    "build_companion_today_bundle",
    "run_companion_interaction",
]
