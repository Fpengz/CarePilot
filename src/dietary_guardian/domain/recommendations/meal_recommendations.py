"""Deterministic meal recommendations.

Applies safety checks, biomarker context, and preference signals to produce
``RecommendationOutput`` for a given ``MealRecognitionRecord``.  All scoring
is rule-based — no LLM calls here.
"""

from dietary_guardian.domain.health.models import ClinicalProfileSnapshot
from dietary_guardian.domain.identity.models import UserProfile
from dietary_guardian.domain.meals.meal_record_accessors import (
    meal_display_name,
    meal_ingredients,
    meal_nutrition,
)
from dietary_guardian.domain.recommendations.models import RecommendationOutput
import logging
from dietary_guardian.domain.meals.models import MealEvent
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord
from dietary_guardian.domain.safety.engine import SafetyEngine, SafetyViolation

logger = logging.getLogger(__name__)

LOCAL_DISH_ALTERNATIVES = {
    "laksa": ["Try fish soup with brown rice", "Ask for less gravy and no extra sambal"],
    "mee rebus": ["Request half noodles and extra bean sprouts", "Skip sweet gravy top-up"],
    "char kway teow": ["Choose yong tau foo soup", "Avoid added lard and sausage"],
}


def _local_advice_for_dish(dish_name: str, user_profile: UserProfile, clinical_snapshot: ClinicalProfileSnapshot) -> list[str]:
    lowered = dish_name.lower()
    for key, advice in LOCAL_DISH_ALTERNATIVES.items():
        if key in lowered:
            base = list(advice)
            break
    else:
        base = ["Choose less gravy and ask for reduced sodium at hawker stalls"]

    goals = {goal.lower() for goal in user_profile.nutrition_goals}
    if "lower_sugar" in goals or clinical_snapshot.biomarkers.get("hba1c", 0) >= 7.0:
        base.append("Prefer unsweetened drinks and smaller refined-carb portions to steady glucose response.")
    if "heart_health" in goals or clinical_snapshot.biomarkers.get("ldl", 0) >= 3.4:
        base.append("Prioritize clearer soups, steamed proteins, and less fried garnish for heart-health support.")
    if user_profile.preferred_cuisines:
        base.append(f"Bias future swaps toward your preferred cuisines: {', '.join(user_profile.preferred_cuisines)}.")
    if user_profile.disliked_ingredients:
        base.append(f"Avoiding your stated dislikes: {', '.join(user_profile.disliked_ingredients)}.")
    return base


def _to_meal_event(record: MealRecognitionRecord) -> MealEvent:
    return MealEvent(
        name=meal_display_name(record),
        ingredients=meal_ingredients(record),
        nutrition=meal_nutrition(record),
    )


def generate_recommendation(
    meal_record: MealRecognitionRecord,
    clinical_snapshot: ClinicalProfileSnapshot,
    user_profile: UserProfile,
) -> RecommendationOutput:
    """Generate a deterministic ``RecommendationOutput`` for the given meal and profile."""
    logger.info(
        "generate_recommendation_start user_id=%s dish=%s biomarkers=%s",
        user_profile.id,
        meal_display_name(meal_record),
        sorted(clinical_snapshot.biomarkers.keys()),
    )
    safety_engine = SafetyEngine(user_profile)
    meal_event = _to_meal_event(meal_record)

    try:
        safety_warnings = safety_engine.validate_meal(meal_event)
    except SafetyViolation as exc:
        logger.warning(
            "generate_recommendation_blocked user_id=%s dish=%s reason=%s",
            user_profile.id,
            meal_display_name(meal_record),
            exc.message,
        )
        return RecommendationOutput(
            safe=False,
            rationale="Safety engine blocked this recommendation due to a contraindication.",
            localized_advice=["Do not consume this meal with current medication regimen."],
            blocked_reason=exc.message,
            evidence=clinical_snapshot.biomarkers,
        )

    biomarkers = clinical_snapshot.biomarkers
    biomarker_line = ", ".join(f"{k}={v}" for k, v in biomarkers.items()) or "no biomarkers available"
    goals_line = ", ".join(user_profile.nutrition_goals) or "general wellness"
    rationale = (
        f"Based on {meal_display_name(meal_record)}, goals ({goals_line}), and biomarkers ({biomarker_line}), "
        "here are localized recommendations for Singapore hawker options."
    )
    advice = _local_advice_for_dish(meal_display_name(meal_record), user_profile, clinical_snapshot)
    for warning in safety_warnings:
        advice.append(warning)

    output = RecommendationOutput(
        safe=True,
        rationale=rationale,
        localized_advice=advice,
        evidence=biomarkers,
    )
    logger.info(
        "generate_recommendation_complete user_id=%s safe=%s advice_items=%s",
        user_profile.id,
        output.safe,
        len(output.localized_advice),
    )
    return output


__all__ = ["generate_recommendation"]
