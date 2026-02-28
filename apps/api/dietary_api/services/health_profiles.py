from __future__ import annotations

from dietary_guardian.logging_config import get_logger
from dietary_guardian.services.daily_suggestions_service import build_daily_suggestions
from dietary_guardian.services.health_profile_service import (
    compute_bmi,
    compute_profile_completeness,
    get_or_create_health_profile,
    resolve_user_profile,
    update_health_profile,
)

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    DailySuggestionBundleResponse,
    DailySuggestionsResponse,
    HealthProfileCondition,
    HealthProfileEnvelopeResponse,
    HealthProfileCompletenessResponse,
    HealthProfileMedication,
    HealthProfileResponseItem,
    HealthProfileUpdateRequest,
)

logger = get_logger(__name__)


def _to_profile_response(*, profile, fallback_mode: bool) -> HealthProfileResponseItem:
    completeness = compute_profile_completeness(profile)
    return HealthProfileResponseItem(
        age=profile.age,
        locale=profile.locale,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        bmi=compute_bmi(profile),
        daily_sodium_limit_mg=profile.daily_sodium_limit_mg,
        daily_sugar_limit_g=profile.daily_sugar_limit_g,
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
        fallback_mode=fallback_mode,
        completeness=HealthProfileCompletenessResponse.model_validate(completeness.model_dump(mode="json")),
        updated_at=profile.updated_at,
    )


def get_profile(*, context: AppContext, session: dict[str, object]) -> HealthProfileEnvelopeResponse:
    profile = get_or_create_health_profile(context.repository, str(session["user_id"]))
    completeness = compute_profile_completeness(profile)
    return HealthProfileEnvelopeResponse(
        profile=_to_profile_response(profile=profile, fallback_mode=completeness.state != "ready")
    )


def patch_profile(
    *,
    context: AppContext,
    session: dict[str, object],
    payload: HealthProfileUpdateRequest,
) -> HealthProfileEnvelopeResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise build_api_error(
            status_code=400,
            code="profile.no_changes_requested",
            message="no health profile changes requested",
        )
    profile = update_health_profile(
        context.repository,
        user_id=str(session["user_id"]),
        updates=updates,
    )
    completeness = compute_profile_completeness(profile)
    return HealthProfileEnvelopeResponse(
        profile=_to_profile_response(profile=profile, fallback_mode=completeness.state != "ready")
    )


def get_daily_suggestions(
    *,
    context: AppContext,
    session: dict[str, object],
) -> DailySuggestionsResponse:
    health_profile, user_profile = resolve_user_profile(context.repository, session)
    completeness = compute_profile_completeness(health_profile)
    fallback_mode = completeness.state != "ready"
    meal_history = context.repository.list_meal_records(str(session["user_id"]))
    biomarker_history = context.repository.list_biomarker_readings(str(session["user_id"]))
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
        profile=_to_profile_response(profile=health_profile, fallback_mode=fallback_mode),
        bundle=DailySuggestionBundleResponse.model_validate(bundle.model_dump(mode="json")),
    )
