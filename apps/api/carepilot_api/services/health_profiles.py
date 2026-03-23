"""API orchestration entry points for health-profile and onboarding workflows.

Shim: business logic lives in care_pilot.features.profiles.profile_service.
"""

from __future__ import annotations

from care_pilot.features.profiles.profile_service import (  # noqa: F401
    complete_profile_onboarding,
    get_daily_suggestions,
    get_profile,
    get_profile_onboarding,
    patch_profile,
    patch_profile_onboarding,
    to_profile_response as _to_profile_response,
)

__all__ = [
    "_to_profile_response",
    "complete_profile_onboarding",
    "get_daily_suggestions",
    "get_profile",
    "get_profile_onboarding",
    "patch_profile",
    "patch_profile_onboarding",
]
