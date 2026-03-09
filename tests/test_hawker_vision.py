import pytest

from dietary_guardian.agents.hawker_vision import HawkerVisionModule
from dietary_guardian.config.runtime import LocalModelProfile
from dietary_guardian.config.settings import get_settings
from dietary_guardian.models.inference import InferenceResponse, ProviderMetadata
from dietary_guardian.models.meal import ImageInput
from dietary_guardian.domain.meals import MealPerception

@pytest.mark.anyio
async def test_hawker_vision_returns_bounded_perception_contract() -> None:
    module = HawkerVisionModule(provider="test")

    result = await module.analyze_dish("laksa with egg")

    assert result.perception is not None
    assert result.perception.meal_detected is True
    assert result.perception.items
    assert result.primary_state.nutrition.calories == 0
    assert result.enriched_event is None


@pytest.mark.anyio
async def test_analyze_and_record_normalizes_into_enriched_event() -> None:
    module = HawkerVisionModule(provider="test")
    image_input = ImageInput(
        source="upload",
        filename="laksa.jpg",
        mime_type="image/jpeg",
        content=b"abc",
    )

    result, record = await module.analyze_and_record(image_input, user_id="u1")

    assert result.perception is not None
    assert result.enriched_event is not None
    assert result.enriched_event.meal_name == "Laksa"
    assert result.primary_state.nutrition.calories > 0
    assert record.enriched_event is not None
    assert record.meal_perception is not None
    assert record.analysis_version == "v2"


@pytest.mark.anyio
async def test_clarification_dialogue_for_very_low_confidence(monkeypatch: pytest.MonkeyPatch) -> None:
    module = HawkerVisionModule(provider="test")

    very_low_confidence = MealPerception.model_validate(
        {
            "meal_detected": True,
            "items": [
                {
                    "label": "Possibly Laksa",
                    "candidate_aliases": ["Laksa"],
                    "portion_estimate": {"amount": 1.0, "unit": "bowl", "confidence": 0.3},
                    "confidence": 0.3,
                }
            ],
            "uncertainties": ["Blurred broth"],
            "image_quality": "poor",
            "confidence_score": 0.30,
        }
    )

    async def fake_infer(*args, **kwargs) -> InferenceResponse:
        del args, kwargs
        return InferenceResponse(
            request_id="req-1",
            structured_output=very_low_confidence,
            confidence=very_low_confidence.confidence_score,
            latency_ms=5.0,
            provider_metadata=ProviderMetadata(provider="test", model="test-model", endpoint="default"),
        )

    monkeypatch.setattr(module.inference_engine, "infer", fake_infer)
    monkeypatch.setattr(module, "provider", "gemini")

    result = await module.analyze_dish("blurred bowl of noodles")

    assert result.needs_manual_review is True
    assert result.primary_state.identification_method == "User_Manual"
    assert result.primary_state.dish_name == "Clarification Required"
    assert result.perception is not None
    assert result.perception.image_quality == "poor"


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
                "output": MealPerception.model_validate(
                    {
                        "meal_detected": True,
                        "items": [
                            {
                                "label": "Mee Rebus",
                                "candidate_aliases": ["Mee Rebus"],
                                "portion_estimate": {"amount": 1.0, "unit": "bowl", "confidence": 0.9},
                                "preparation": "soup",
                                "confidence": 0.95,
                            }
                        ],
                        "uncertainties": [],
                        "image_quality": "good",
                        "confidence_score": 0.95,
                    }
                )
            },
        )()

    monkeypatch.setattr(module.inference_engine, "infer", fail_infer)
    monkeypatch.setattr(module.agent, "run", fake_run)
    monkeypatch.setattr(module, "provider", "gemini")

    result = await module.analyze_dish("mee rebus")

    assert result.primary_state.dish_name == "Mee Rebus"
    assert result.needs_manual_review is False
    get_settings.cache_clear()
