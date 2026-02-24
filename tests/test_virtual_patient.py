from hypothesis import given, strategies as st
from dietary_guardian.models.meal import MealEvent, Ingredient, Nutrition
from dietary_guardian.models.user import UserProfile, MedicalCondition, Medication
from dietary_guardian.safety.engine import SafetyEngine, SafetyViolation
from dietary_guardian.safety.db import DrugInteractionDB
import pytest

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
