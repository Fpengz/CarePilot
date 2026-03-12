"""Tests for chat context formatting."""

from dietary_guardian.features.companion.core.domain import CaseSnapshot
from dietary_guardian.features.meals.domain.models import Ingredient, MealState, Nutrition, PortionSize
from dietary_guardian.features.meals.domain.recognition import MealRecognitionRecord
from dietary_guardian.features.companion.core.chat_context import format_chat_context


def test_format_chat_context_includes_profile_and_meals() -> None:
    snapshot = CaseSnapshot(
        user_id="u1",
        profile_name="Alex",
        conditions=["hypertension"],
        medications=["amlodipine"],
        meal_count=2,
        latest_meal_name="Chicken Rice",
        meal_risk_streak=1,
        reminder_count=3,
        reminder_response_rate=0.5,
        adherence_events=2,
        adherence_rate=0.75,
        symptom_count=1,
        average_symptom_severity=2.0,
        biomarker_summary={"ldl": 3.2},
        active_risk_flags=["high_sodium"],
    )

    meal_state = MealState(
        dish_name="Chicken Rice",
        confidence_score=0.8,
        identification_method="AI_Flash",
        ingredients=[Ingredient(name="chicken"), Ingredient(name="rice")],
        nutrition=Nutrition(calories=620, carbs_g=80, sugar_g=4, protein_g=25, fat_g=20, sodium_mg=900),
        portion_size=PortionSize.STANDARD,
    )
    meals = [
        MealRecognitionRecord(id="m1", user_id="u1", source="chat", meal_state=meal_state),
    ]

    context = format_chat_context(snapshot=snapshot, recent_meals=meals)

    assert "Profile: Alex" in context
    assert "Conditions: hypertension" in context
    assert "Latest meal: Chicken Rice" in context
    assert "Recent meals:" in context
    assert "Chicken Rice" in context
