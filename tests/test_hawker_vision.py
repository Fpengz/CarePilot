from types import SimpleNamespace

import pytest

from dietary_guardian.agents.hawker_vision import HawkerVisionModule
from dietary_guardian.models.meal import MealState, Nutrition

def test_safe_fail_fallback():
    """
    Test that Tier 3 'Safe-Fail' triggers when confidence < 75%.
    """
    module = HawkerVisionModule()

    # Mock a low confidence result
    low_conf_state = MealState(
        dish_name="Mee Siam",
        confidence_score=0.60,  # < 0.75
        identification_method="AI_Flash",
        ingredients=[],
        nutrition=Nutrition(
            calories=0, carbs_g=0, sugar_g=0, protein_g=0, fat_g=0, sodium_mg=0
        ),
    )

    # Apply fallback logic
    result_state = module._apply_fallback_logic(low_conf_state)

    assert result_state.identification_method == "HPB_Fallback"
    assert result_state.nutrition.sodium_mg == 2660  # From HPB_DATABASE
    assert "Health Promotion Board" in result_state.suggested_modifications[0]

def test_localization_logic():
    """
    Verify the model structure supports localization.
    """
    state = MealState(
        dish_name="Mee Rebus",
        confidence_score=0.95,
        identification_method="AI_Flash",
        ingredients=[],
        nutrition=Nutrition(
            calories=570, carbs_g=60, sugar_g=10, protein_g=15, fat_g=20, sodium_mg=2100
        ),
    )
    assert "Mee Rebus" in state.dish_name
    assert state.localization.variant is None  # Default


@pytest.mark.anyio
async def test_clarification_dialogue_for_very_low_confidence(monkeypatch: pytest.MonkeyPatch) -> None:
    module = HawkerVisionModule(provider="test")

    very_low_conf_state = MealState(
        dish_name="Possibly Laksa",
        confidence_score=0.30,  # < 0.40, should trigger clarification flow
        identification_method="AI_Flash",
        ingredients=[],
        nutrition=Nutrition(
            calories=450, carbs_g=50, sugar_g=8, protein_g=15, fat_g=18, sodium_mg=900
        ),
    )

    async def fake_run(_: str) -> SimpleNamespace:
        return SimpleNamespace(output=very_low_conf_state)

    monkeypatch.setattr(module.agent, "run", fake_run)

    result = await module.analyze_dish("blurred bowl of noodles")

    assert result.needs_manual_review is True
    assert result.primary_state.identification_method == "User_Manual"
    assert result.primary_state.dish_name == "Clarification Required"
    assert any("clarification" in tip.lower() for tip in result.primary_state.suggested_modifications)
