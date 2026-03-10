"""Tests for safety."""

import pytest

from dietary_guardian.domain.identity.models import (
    MedicalCondition,
    Medication,
    UserProfile,
)
from dietary_guardian.models.meal import Ingredient, MealEvent, Nutrition
from dietary_guardian.safety.engine import SafetyEngine, SafetyViolation


@pytest.fixture
def mr_tan():
    return UserProfile(
        id="user_001",
        name="Mr. Tan",
        age=68,
        conditions=[MedicalCondition(name="Hypertension", severity="Medium")],
        medications=[
            Medication(name="Warfarin", dosage="5mg", contraindications={"Spinach"})
        ],
    )


def test_sodium_warning(mr_tan):
    engine = SafetyEngine(mr_tan)
    high_sodium_meal = MealEvent(
        name="High Salt Ramen",
        ingredients=[Ingredient(name="Noodles")],
        nutrition=Nutrition(
            calories=500,
            carbs_g=50,
            sugar_g=2,
            protein_g=10,
            fat_g=10,
            sodium_mg=1500,  # > 1000mg (50% of 2000mg)
        ),
    )
    warnings = engine.validate_meal(high_sodium_meal)
    assert any("High Sodium Alert" in w for w in warnings)


def test_medication_violation(mr_tan):
    engine = SafetyEngine(mr_tan)
    spinach_meal = MealEvent(
        name="Spinach Salad",
        ingredients=[Ingredient(name="Spinach")],
        nutrition=Nutrition(
            calories=50, carbs_g=5, sugar_g=1, protein_g=2, fat_g=0, sodium_mg=100
        ),
    )
    with pytest.raises(SafetyViolation) as excinfo:
        engine.validate_meal(spinach_meal)
    assert "CRITICAL SAFETY ALERT" in str(excinfo.value)
    assert "Warfarin" in str(excinfo.value)
