"""Tests for recommendation safety override."""

from datetime import datetime

from dietary_guardian.domain.health.models import ClinicalProfileSnapshot
from dietary_guardian.domain.identity.models import (
    MedicalCondition,
    Medication,
    UserProfile,
)
from dietary_guardian.domain.meals.models import Ingredient, MealState, Nutrition
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord
from dietary_guardian.domain.recommendations.meal_recommendations import generate_recommendation


def test_safety_override_blocks_recommendation() -> None:
    user = UserProfile(
        id="u1",
        name="Mr Tan",
        age=68,
        conditions=[MedicalCondition(name="Hypertension", severity="High")],
        medications=[Medication(name="Warfarin", dosage="5mg")],
    )
    record = MealRecognitionRecord(
        id="m1",
        user_id="u1",
        captured_at=datetime(2026, 2, 24, 12, 0),
        source="upload",
        meal_state=MealState(
            dish_name="Spinach Soup",
            confidence_score=0.95,
            identification_method="AI_Flash",
            ingredients=[Ingredient(name="Spinach")],
            nutrition=Nutrition(calories=150, carbs_g=10, sugar_g=1, protein_g=6, fat_g=4, sodium_mg=400),
        ),
    )
    rec = generate_recommendation(record, ClinicalProfileSnapshot(biomarkers={"ldl": 3.8}), user)
    assert rec.safe is False
    assert rec.blocked_reason is not None
