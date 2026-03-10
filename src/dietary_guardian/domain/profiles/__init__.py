"""Domain profiles package.

Re-exports health profile domain rules and onboarding state machine.
"""

from dietary_guardian.domain.profiles.health_profile import (
    DEFAULT_PROFILE_AGE,
    HealthProfileRepository,
    build_user_profile_from_health_profile,
    compute_bmi,
    compute_profile_completeness,
    default_health_profile,
    get_or_create_health_profile,
    resolve_user_profile,
    update_health_profile,
)
from dietary_guardian.domain.profiles.onboarding import (
    ONBOARDING_STEP_DEFINITIONS,
    ONBOARDING_STEP_IDS,
    HealthProfileOnboardingRepository,
    complete_health_profile_onboarding,
    default_health_profile_onboarding_state,
    get_or_create_health_profile_onboarding_state,
    list_onboarding_steps,
    update_health_profile_onboarding,
)

__all__ = [
    "DEFAULT_PROFILE_AGE",
    "ONBOARDING_STEP_DEFINITIONS",
    "ONBOARDING_STEP_IDS",
    "HealthProfileOnboardingRepository",
    "HealthProfileRepository",
    "build_user_profile_from_health_profile",
    "complete_health_profile_onboarding",
    "compute_bmi",
    "compute_profile_completeness",
    "default_health_profile",
    "default_health_profile_onboarding_state",
    "get_or_create_health_profile",
    "get_or_create_health_profile_onboarding_state",
    "list_onboarding_steps",
    "resolve_user_profile",
    "update_health_profile",
    "update_health_profile_onboarding",
]
