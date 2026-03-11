"""Tests for virtual patient."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dietary_guardian.domain.identity.models import (
    MedicalCondition,
    Medication,
    UserProfile,
)
from dietary_guardian.domain.meals.models import Ingredient, MealEvent, Nutrition
from dietary_guardian.infrastructure.safety.drug_interaction_db import DrugInteractionDB
from dietary_guardian.domain.safety.engine import SafetyEngine, SafetyViolation

# Clinical setup for Mr. Tan
mr_tan = UserProfile(
    id="user_001",
    name="Mr. Tan",
    age=68,
    conditions=[MedicalCondition(name="Diabetes", severity="High")],
    medications=[Medication(name="Warfarin", dosage="5mg")],
)

# Hypothesis strategies for randomized meals
ingredient_strategy = st.builds(Ingredient, name=st.text(min_size=1, max_size=20))
nutrition_strategy = st.builds(
    Nutrition,
    calories=st.floats(min_value=0, max_value=2000),
    carbs_g=st.floats(min_value=0, max_value=200),
    sugar_g=st.floats(min_value=0, max_value=100),
    protein_g=st.floats(min_value=0, max_value=100),
    fat_g=st.floats(min_value=0, max_value=100),
    sodium_mg=st.floats(min_value=0, max_value=5000),
)
meal_strategy = st.builds(
    MealEvent,
    name=st.text(min_size=1),
    ingredients=st.lists(ingredient_strategy, min_size=1, max_size=10),
    nutrition=nutrition_strategy,
)


@settings(deadline=None)
@given(meal_strategy)
def test_safety_invariants(meal):
    """
    Property: If a meal contains 'Spinach' and the user is on 'Warfarin',
    a SafetyViolation MUST be raised.
    """
    engine = SafetyEngine(mr_tan)

    # Check if 'Spinach' is in ingredients (case insensitive)
    has_spinach = any("spinach" in i.name.lower() for i in meal.ingredients)

    if has_spinach:
        with pytest.raises(SafetyViolation):
            engine.validate_meal(meal)
    else:
        # Should not raise Critical violation for ingredients (unless it's another contraindication)
        try:
            engine.validate_meal(meal)
        except SafetyViolation:
            # If it raises, it must be because of another known restricted item like Kale
            restricted_items = [i.name.lower() for i in meal.ingredients]
            assert any(x in ["kale", "ginkgo"] for x in restricted_items)


def test_hpb_db_integration():
    db = DrugInteractionDB()
    contras = db.get_contraindications("Warfarin")
    assert any(c[0] == "Spinach" for c in contras)
    assert any(c[2] == "Critical" for c in contras)


def test_maoi_interaction_escalates_for_tyramine_rich_foods() -> None:
    user = UserProfile(
        id="user_002",
        name="Ms. Lim",
        age=61,
        conditions=[MedicalCondition(name="Depression", severity="Medium")],
        medications=[Medication(name="Phenelzine", dosage="15mg")],
    )
    meal = MealEvent(
        name="Cheese platter",
        ingredients=[Ingredient(name="Aged Cheese"), Ingredient(name="Crackers")],
        nutrition=Nutrition(
            calories=320,
            carbs_g=20,
            sugar_g=3,
            protein_g=16,
            fat_g=22,
            sodium_mg=620,
        ),
    )
    with pytest.raises(SafetyViolation):
        SafetyEngine(user).validate_meal(meal)


def test_low_carb_meal_warns_for_insulin_users() -> None:
    user = UserProfile(
        id="user_003",
        name="Mr. Goh",
        age=66,
        conditions=[MedicalCondition(name="Type 2 Diabetes", severity="High")],
        medications=[Medication(name="Insulin", dosage="10 units")],
    )
    meal = MealEvent(
        name="Plain omelette",
        ingredients=[Ingredient(name="Egg"), Ingredient(name="Oil")],
        nutrition=Nutrition(
            calories=210,
            carbs_g=4,
            sugar_g=1,
            protein_g=14,
            fat_g=15,
            sodium_mg=240,
        ),
    )
    warnings = SafetyEngine(user).validate_meal(meal)
    assert any("Hypoglycemia Risk" in item for item in warnings)


def test_compound_multi_medication_risk_raises_critical() -> None:
    user = UserProfile(
        id="user_004",
        name="Mr. Ong",
        age=70,
        conditions=[MedicalCondition(name="Atrial fibrillation", severity="High")],
        medications=[
            Medication(name="Warfarin", dosage="5mg"),
            Medication(name="Atorvastatin", dosage="20mg"),
        ],
    )
    meal = MealEvent(
        name="Green smoothie",
        ingredients=[Ingredient(name="Spinach"), Ingredient(name="Grapefruit")],
        nutrition=Nutrition(
            calories=260,
            carbs_g=28,
            sugar_g=16,
            protein_g=5,
            fat_g=8,
            sodium_mg=90,
        ),
    )
    with pytest.raises(SafetyViolation):
        SafetyEngine(user).validate_meal(meal)
