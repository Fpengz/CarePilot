"""Tests for recommendation localization sg."""

from datetime import datetime

from dietary_guardian.domain.health.models import ClinicalProfileSnapshot
from dietary_guardian.domain.identity.models import (
    MedicalCondition,
    Medication,
    UserProfile,
)
from dietary_guardian.domain.meals.models import MealState, Nutrition
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord
from dietary_guardian.domain.recommendations.meal_recommendations import generate_recommendation


def test_recommendation_uses_sg_local_advice() -> None:
    user = UserProfile(
        id="u1",
        name="Mr Tan",
        age=68,
        conditions=[MedicalCondition(name="Hypertension", severity="High")],
        medications=[Medication(name="Amlodipine", dosage="5mg")],
    )
    record = MealRecognitionRecord(
        id="m1",
        user_id="u1",
        captured_at=datetime(2026, 2, 24, 12, 0),
        source="upload",
        meal_state=MealState(
            dish_name="Char Kway Teow",
            confidence_score=0.95,
            identification_method="AI_Flash",
            ingredients=[],
            nutrition=Nutrition(calories=700, carbs_g=80, sugar_g=6, protein_g=20, fat_g=35, sodium_mg=1500),
        ),
    )
    rec = generate_recommendation(record, ClinicalProfileSnapshot(biomarkers={}), user)
    joined = " ".join(rec.localized_advice).lower()
    assert "yong tau foo" in joined
