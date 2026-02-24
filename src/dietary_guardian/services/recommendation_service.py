from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.meal import MealEvent
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.models.recommendation import RecommendationOutput
from dietary_guardian.models.report import ClinicalProfileSnapshot
from dietary_guardian.models.user import UserProfile
from dietary_guardian.safety.engine import SafetyEngine, SafetyViolation

logger = get_logger(__name__)

LOCAL_DISH_ALTERNATIVES = {
    "laksa": ["Try fish soup with brown rice", "Ask for less gravy and no extra sambal"],
    "mee rebus": ["Request half noodles and extra bean sprouts", "Skip sweet gravy top-up"],
    "char kway teow": ["Choose yong tau foo soup", "Avoid added lard and sausage"],
}


def _local_advice_for_dish(dish_name: str) -> list[str]:
    lowered = dish_name.lower()
    for key, advice in LOCAL_DISH_ALTERNATIVES.items():
        if key in lowered:
            return advice
    return ["Choose less gravy and ask for reduced sodium at hawker stalls"]


def _to_meal_event(record: MealRecognitionRecord) -> MealEvent:
    return MealEvent(
        name=record.meal_state.dish_name,
        ingredients=record.meal_state.ingredients,
        nutrition=record.meal_state.nutrition,
    )


def generate_recommendation(
    meal_record: MealRecognitionRecord,
    clinical_snapshot: ClinicalProfileSnapshot,
    user_profile: UserProfile,
) -> RecommendationOutput:
    logger.info(
        "generate_recommendation_start user_id=%s dish=%s biomarkers=%s",
        user_profile.id,
        meal_record.meal_state.dish_name,
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
            meal_record.meal_state.dish_name,
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
    rationale = (
        f"Based on {meal_record.meal_state.dish_name} and biomarkers ({biomarker_line}), "
        "here are localized recommendations for Singapore hawker options."
    )
    advice = _local_advice_for_dish(meal_record.meal_state.dish_name)
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
