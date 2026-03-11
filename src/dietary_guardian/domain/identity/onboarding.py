"""Health profile onboarding domain rules and repository protocol.

Defines the step sequence, onboarding state machine transitions, and the
``HealthProfileOnboardingRepository`` protocol.  Pure domain logic — no HTTP
or persistence imports.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from dietary_guardian.domain.health.models import (
    HealthProfileOnboardingState,
    HealthProfileOnboardingStepDefinition,
    HealthProfileRecord,
)
from dietary_guardian.domain.identity.health_profile import (
    HealthProfileRepository,
    get_or_create_health_profile,
    update_health_profile,
)


class HealthProfileOnboardingRepository(HealthProfileRepository, Protocol):
    def get_health_profile_onboarding_state(self, user_id: str) -> HealthProfileOnboardingState | None: ...

    def save_health_profile_onboarding_state(
        self,
        state: HealthProfileOnboardingState,
    ) -> HealthProfileOnboardingState: ...


ONBOARDING_STEP_DEFINITIONS: tuple[HealthProfileOnboardingStepDefinition, ...] = (
    HealthProfileOnboardingStepDefinition(
        id="basic_identity",
        title="Basic Identity",
        description="Capture the age, locale, and body measurements needed for baseline guidance.",
        fields=["age", "locale", "height_cm", "weight_kg"],
    ),
    HealthProfileOnboardingStepDefinition(
        id="health_context",
        title="Health Context",
        description="Record current conditions and medications so downstream recommendations stay cautious.",
        fields=["conditions", "medications"],
    ),
    HealthProfileOnboardingStepDefinition(
        id="nutrition_targets",
        title="Nutrition Targets",
        description="Set the daily nutrient targets used across meal tracking and reminder logic.",
        fields=[
            "daily_sodium_limit_mg",
            "daily_sugar_limit_g",
            "daily_protein_target_g",
            "daily_fiber_target_g",
            "target_calories_per_day",
            "macro_focus",
            "nutrition_goals",
        ],
    ),
    HealthProfileOnboardingStepDefinition(
        id="preferences",
        title="Preferences",
        description="Capture cuisine preferences, budget, allergies, and ingredient dislikes.",
        fields=["preferred_cuisines", "allergies", "disliked_ingredients", "budget_tier"],
    ),
    HealthProfileOnboardingStepDefinition(
        id="review",
        title="Review",
        description="Review the profile summary before marking setup complete.",
        fields=[],
    ),
)

ONBOARDING_STEP_IDS = tuple(step.id for step in ONBOARDING_STEP_DEFINITIONS)


def list_onboarding_steps() -> list[HealthProfileOnboardingStepDefinition]:
    return [step.model_copy(deep=True) for step in ONBOARDING_STEP_DEFINITIONS]


def default_health_profile_onboarding_state(user_id: str) -> HealthProfileOnboardingState:
    return HealthProfileOnboardingState(
        user_id=user_id,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


def get_or_create_health_profile_onboarding_state(
    repository: HealthProfileOnboardingRepository,
    user_id: str,
) -> HealthProfileOnboardingState:
    stored = repository.get_health_profile_onboarding_state(user_id)
    if stored is not None:
        return stored
    return default_health_profile_onboarding_state(user_id)


def update_health_profile_onboarding(
    repository: HealthProfileOnboardingRepository,
    *,
    user_id: str,
    step_id: str,
    profile_updates: dict[str, object],
) -> tuple[HealthProfileOnboardingState, HealthProfileRecord]:
    if step_id not in ONBOARDING_STEP_IDS:
        raise ValueError("invalid onboarding step")
    profile = (
        update_health_profile(repository, user_id=user_id, updates=profile_updates)
        if profile_updates
        else get_or_create_health_profile(repository, user_id)
    )
    state = get_or_create_health_profile_onboarding_state(repository, user_id)
    completed_steps = [item for item in ONBOARDING_STEP_IDS if item in {*state.completed_steps, step_id}]
    current_step = _next_onboarding_step(step_id=step_id, completed_steps=completed_steps)
    next_state = HealthProfileOnboardingState(
        user_id=user_id,
        current_step=current_step,
        completed_steps=completed_steps,
        is_complete=state.is_complete,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    return repository.save_health_profile_onboarding_state(next_state), profile


def complete_health_profile_onboarding(
    repository: HealthProfileOnboardingRepository,
    *,
    user_id: str,
) -> tuple[HealthProfileOnboardingState, HealthProfileRecord]:
    profile = get_or_create_health_profile(repository, user_id)
    state = HealthProfileOnboardingState(
        user_id=user_id,
        current_step="review",
        completed_steps=list(ONBOARDING_STEP_IDS),
        is_complete=True,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    return repository.save_health_profile_onboarding_state(state), profile


def _next_onboarding_step(*, step_id: str, completed_steps: list[str]) -> str:
    current_index = ONBOARDING_STEP_IDS.index(step_id)
    for candidate in ONBOARDING_STEP_IDS[current_index + 1 :]:
        if candidate not in completed_steps:
            return candidate
    return "review"


__all__ = [
    "ONBOARDING_STEP_DEFINITIONS",
    "ONBOARDING_STEP_IDS",
    "HealthProfileOnboardingRepository",
    "complete_health_profile_onboarding",
    "default_health_profile_onboarding_state",
    "get_or_create_health_profile_onboarding_state",
    "list_onboarding_steps",
    "update_health_profile_onboarding",
]
