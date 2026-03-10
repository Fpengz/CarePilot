"""Application use cases for health profiles and onboarding workflows."""

from __future__ import annotations

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    DailySuggestionBundleResponse,
    DailySuggestionsResponse,
    GuidedHealthStepResponse,
    HealthProfileCompletenessResponse,
    HealthProfileCondition,
    HealthProfileEnvelopeResponse,
    HealthProfileMedication,
    HealthProfileOnboardingEnvelopeResponse,
    HealthProfileOnboardingPatchRequest,
    HealthProfileOnboardingStateResponse,
    HealthProfileResponseItem,
    HealthProfileUpdateRequest,
)
from dietary_guardian.application.recommendations.daily_suggestions import build_daily_suggestions
from dietary_guardian.domain.identity.health_profile import (
    compute_bmi,
    compute_profile_completeness,
    get_or_create_health_profile,
    resolve_user_profile,
    update_health_profile,
)
from dietary_guardian.domain.identity.onboarding import (
    complete_health_profile_onboarding,
    get_or_create_health_profile_onboarding_state,
    list_onboarding_steps,
    update_health_profile_onboarding,
)
from dietary_guardian.infrastructure.observability import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared response helper (moved from _health_profile_support.py)
# ---------------------------------------------------------------------------

def to_profile_response(*, profile, fallback_mode: bool) -> HealthProfileResponseItem:
    """Project a domain health profile into the API response shape."""
    completeness = compute_profile_completeness(profile)
    return HealthProfileResponseItem(
        age=profile.age,
        locale=profile.locale,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        bmi=compute_bmi(profile),
        daily_sodium_limit_mg=profile.daily_sodium_limit_mg,
        daily_sugar_limit_g=profile.daily_sugar_limit_g,
        daily_protein_target_g=profile.daily_protein_target_g,
        daily_fiber_target_g=profile.daily_fiber_target_g,
        target_calories_per_day=profile.target_calories_per_day,
        macro_focus=profile.macro_focus,
        conditions=[
            HealthProfileCondition.model_validate(item.model_dump(mode="json")) for item in profile.conditions
        ],
        medications=[
            HealthProfileMedication.model_validate(
                {**item.model_dump(mode="json"), "contraindications": sorted(item.contraindications)}
            )
            for item in profile.medications
        ],
        allergies=profile.allergies,
        nutrition_goals=profile.nutrition_goals,
        preferred_cuisines=profile.preferred_cuisines,
        disliked_ingredients=profile.disliked_ingredients,
        budget_tier=profile.budget_tier,
        meal_schedule=profile.meal_schedule,
        preferred_notification_channel=profile.preferred_notification_channel,
        fallback_mode=fallback_mode,
        completeness=HealthProfileCompletenessResponse.model_validate(completeness.model_dump(mode="json")),
        updated_at=profile.updated_at,
    )


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _to_onboarding_response(*, state, profile) -> HealthProfileOnboardingEnvelopeResponse:
    completeness = compute_profile_completeness(profile)
    return HealthProfileOnboardingEnvelopeResponse(
        onboarding=HealthProfileOnboardingStateResponse(
            current_step=state.current_step,
            completed_steps=list(state.completed_steps),
            is_complete=state.is_complete,
            updated_at=state.updated_at,
        ),
        profile=to_profile_response(profile=profile, fallback_mode=completeness.state != "ready"),
        steps=[
            GuidedHealthStepResponse(
                id=step.id,
                title=step.title,
                description=step.description,
                fields=list(step.fields),
            )
            for step in list_onboarding_steps()
        ],
    )


# ---------------------------------------------------------------------------
# Use cases
# ---------------------------------------------------------------------------

def get_profile(*, context: AppContext, session: dict[str, object]) -> HealthProfileEnvelopeResponse:
    """Fetch or initialize the active user's health profile."""
    profile = get_or_create_health_profile(context.stores.profiles, str(session["user_id"]))
    completeness = compute_profile_completeness(profile)
    return HealthProfileEnvelopeResponse(
        profile=to_profile_response(profile=profile, fallback_mode=completeness.state != "ready")
    )


def patch_profile(
    *,
    context: AppContext,
    session: dict[str, object],
    payload: HealthProfileUpdateRequest,
) -> HealthProfileEnvelopeResponse:
    """Apply a partial update to the active user's health profile."""
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise build_api_error(
            status_code=400,
            code="profile.no_changes_requested",
            message="no health profile changes requested",
        )
    profile = update_health_profile(
        context.stores.profiles,
        user_id=str(session["user_id"]),
        updates=updates,
    )
    completeness = compute_profile_completeness(profile)
    return HealthProfileEnvelopeResponse(
        profile=to_profile_response(profile=profile, fallback_mode=completeness.state != "ready")
    )


def get_profile_onboarding(*, context: AppContext, session: dict[str, object]) -> HealthProfileOnboardingEnvelopeResponse:
    """Fetch onboarding progress together with the current health-profile state."""
    user_id = str(session["user_id"])
    state = get_or_create_health_profile_onboarding_state(context.stores.profiles, user_id)
    profile = get_or_create_health_profile(context.stores.profiles, user_id)
    return _to_onboarding_response(state=state, profile=profile)


def patch_profile_onboarding(
    *,
    context: AppContext,
    session: dict[str, object],
    payload: HealthProfileOnboardingPatchRequest,
) -> HealthProfileOnboardingEnvelopeResponse:
    """Apply a step-scoped update to the health-profile onboarding workflow."""
    try:
        state, profile = update_health_profile_onboarding(
            context.stores.profiles,
            user_id=str(session["user_id"]),
            step_id=payload.step_id.strip(),
            profile_updates=payload.profile.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise build_api_error(
            status_code=400,
            code="profile.onboarding.invalid_step",
            message="invalid health profile onboarding step",
        ) from exc
    return _to_onboarding_response(state=state, profile=profile)


def complete_profile_onboarding(
    *,
    context: AppContext,
    session: dict[str, object],
) -> HealthProfileOnboardingEnvelopeResponse:
    """Mark health-profile onboarding complete for the active user."""
    state, profile = complete_health_profile_onboarding(
        context.stores.profiles,
        user_id=str(session["user_id"]),
    )
    return _to_onboarding_response(state=state, profile=profile)


def get_daily_suggestions(
    *,
    context: AppContext,
    session: dict[str, object],
) -> DailySuggestionsResponse:
    """Build daily suggestions from the active user's profile and history."""
    health_profile, user_profile = resolve_user_profile(context.stores.profiles, session)
    completeness = compute_profile_completeness(health_profile)
    fallback_mode = completeness.state != "ready"
    meal_history = context.stores.meals.list_meal_records(str(session["user_id"]))
    biomarker_history = context.stores.biomarkers.list_biomarker_readings(str(session["user_id"]))
    logger.info(
        "event=daily_suggestions_generate user_id=%s request_profile_state=%s fallback_mode=%s",
        session["user_id"],
        completeness.state,
        fallback_mode,
    )
    bundle = build_daily_suggestions(
        health_profile=health_profile,
        user_profile=user_profile,
        meal_history=meal_history,
        biomarker_history=biomarker_history,
        fallback_mode=fallback_mode,
    )
    return DailySuggestionsResponse(
        profile=to_profile_response(profile=health_profile, fallback_mode=fallback_mode),
        bundle=DailySuggestionBundleResponse.model_validate(bundle.model_dump(mode="json")),
    )


__all__ = [
    "_to_onboarding_response",
    "complete_profile_onboarding",
    "get_daily_suggestions",
    "get_profile",
    "get_profile_onboarding",
    "patch_profile",
    "patch_profile_onboarding",
    "to_profile_response",
]
