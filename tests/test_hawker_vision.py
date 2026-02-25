import pytest

from dietary_guardian.agents.hawker_vision import HawkerVisionModule
from dietary_guardian.config.settings import get_settings
from dietary_guardian.config.runtime import LocalModelProfile
from dietary_guardian.models.inference import InferenceResponse, ProviderMetadata
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

    assert result_state is not low_conf_state
    assert low_conf_state.identification_method == "AI_Flash"
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

    async def fake_infer(*args, **kwargs) -> InferenceResponse:
        del args, kwargs
        return InferenceResponse(
            request_id="req-1",
            structured_output=very_low_conf_state,
            confidence=very_low_conf_state.confidence_score,
            latency_ms=5.0,
            provider_metadata=ProviderMetadata(provider="test", model="test-model", endpoint="default"),
        )

    monkeypatch.setattr(module.inference_engine, "infer", fake_infer)

    result = await module.analyze_dish("blurred bowl of noodles")

    assert result.needs_manual_review is True
    assert result.primary_state.identification_method == "User_Manual"
    assert result.primary_state.dish_name == "Clarification Required"
    assert any("clarification" in tip.lower() for tip in result.primary_state.suggested_modifications)


def test_hawker_vision_uses_profile_built_model_for_inference_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProvider:
        base_url = "http://profile-specific:9000/v1"

    class FakeModel:
        model_name = "profile-model"
        provider = FakeProvider()

    class StubEngine:
        seen_model = None

        def __init__(self, provider=None, model_name=None, model=None):
            del provider, model_name
            StubEngine.seen_model = model

    monkeypatch.setattr("dietary_guardian.agents.hawker_vision.LLMFactory.from_profile", lambda profile: FakeModel())
    monkeypatch.setattr("dietary_guardian.agents.hawker_vision.InferenceEngine", StubEngine)

    profile = LocalModelProfile(
        id="custom",
        provider="vllm",
        model_name="profile-model",
        base_url="http://profile-specific:9000/v1",
    )

    HawkerVisionModule(local_profile=profile)

    assert StubEngine.seen_model is not None
    assert getattr(StubEngine.seen_model, "provider").base_url == "http://profile-specific:9000/v1"


@pytest.mark.anyio
async def test_hawker_vision_feature_flag_disables_inference_engine_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("USE_INFERENCE_ENGINE_V2", "false")
    get_settings.cache_clear()

    module = HawkerVisionModule(provider="test")

    async def fail_infer(*args, **kwargs):  # noqa: ANN001
        del args, kwargs
        raise AssertionError("inference engine should not be used when v2 is disabled")

    async def fake_run(prompt: str):
        del prompt
        return type(
            "Result",
            (),
            {
                "output": MealState(
                    dish_name="Mee Rebus",
                    confidence_score=0.95,
                    identification_method="AI_Flash",
                    ingredients=[],
                    nutrition=Nutrition(
                        calories=500,
                        carbs_g=60,
                        sugar_g=10,
                        protein_g=20,
                        fat_g=18,
                        sodium_mg=900,
                    ),
                )
            },
        )()

    monkeypatch.setattr(module.inference_engine, "infer", fail_infer)
    monkeypatch.setattr(module.agent, "run", fake_run)

    result = await module.analyze_dish("mee rebus")

    assert result.primary_state.dish_name == "Mee Rebus"
    assert result.needs_manual_review is False
    get_settings.cache_clear()
