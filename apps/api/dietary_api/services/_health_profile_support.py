"""Shared response helpers for health-profile API services."""

from __future__ import annotations

from dietary_guardian.services.health_profile_service import compute_bmi, compute_profile_completeness

from apps.api.dietary_api.schemas import (
    HealthProfileCompletenessResponse,
    HealthProfileCondition,
    HealthProfileMedication,
    HealthProfileResponseItem,
)


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


__all__ = ["to_profile_response"]
