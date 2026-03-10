"""Tests for recommendation grounding."""

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


def _user() -> UserProfile:
    return UserProfile(
        id="u1",
        name="Mr Tan",
        age=68,
        conditions=[MedicalCondition(name="Diabetes", severity="High")],
        medications=[Medication(name="Metformin", dosage="500mg")],
    )


def _record(dish: str, ingredients: list[Ingredient] | None = None) -> MealRecognitionRecord:
    return MealRecognitionRecord(
        id="m1",
        user_id="u1",
        captured_at=datetime(2026, 2, 24, 12, 0),
        source="upload",
        meal_state=MealState(
            dish_name=dish,
            confidence_score=0.9,
            identification_method="AI_Flash",
            ingredients=ingredients or [],
            nutrition=Nutrition(calories=550, carbs_g=60, sugar_g=8, protein_g=18, fat_g=25, sodium_mg=1200),
        ),
    )


def test_recommendation_includes_biomarker_citation() -> None:
    rec = generate_recommendation(
        _record("Laksa"),
        ClinicalProfileSnapshot(biomarkers={"ldl": 4.2, "hba1c": 7.1}),
        _user(),
    )
    assert rec.safe is True
    assert "ldl=4.2" in rec.rationale.lower()
    assert "hba1c=7.1" in rec.rationale.lower()
