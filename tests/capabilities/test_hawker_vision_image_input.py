from typing import cast

import pytest

from dietary_guardian.agent.meal_analysis import HawkerVisionModule
from dietary_guardian.agent.runtime.inference_types import (
    InferenceModality,
    InferenceRequest,
    InferenceResponse,
    ProviderMetadata,
)
from dietary_guardian.config.app import get_settings
from dietary_guardian.features.meals.domain.models import ImageInput, MealPerception


@pytest.mark.anyio
async def test_binary_image_input_returns_safe_clarification_in_test_mode() -> None:
    module = HawkerVisionModule(provider="test")
    image_input = ImageInput(
        source="upload",
        filename="hawker.jpg",
        mime_type="image/jpeg",
        content=b"\xff\xd8\xff",
    )

    result = await module.analyze_dish(image_input)

    assert result.needs_manual_review is False
    assert result.primary_state.identification_method == "AI_Flash"
    assert result.perception is not None
    assert result.perception.meal_detected is True
    assert result.primary_state.dish_name == "hawker"


@pytest.mark.anyio
async def test_binary_image_input_passes_image_bytes_to_inference_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_USE_INFERENCE_ENGINE_V2", "true")
    get_settings.cache_clear()

    seen: dict[str, object] = {}

    class _StubModel:
        model_name = "stub-model"

    class StubEngine:
        def __init__(self, provider=None, model_name=None, model=None):  # noqa: ANN001
            del model_name
            self.provider = provider or "stub"
            self.model = model or _StubModel()

        async def infer(self, request):  # noqa: ANN001
            seen["request"] = request
            perception = MealPerception.model_validate(
                {
                    "meal_detected": True,
                    "items": [
                        {
                            "label": "Char Kway Teow",
                            "candidate_aliases": ["Char Kway Teow"],
                            "portion_estimate": {"amount": 1.0, "unit": "plate", "confidence": 0.9},
                            "preparation": "fried",
                            "confidence": 0.9,
                        }
                    ],
                    "uncertainties": [],
                    "image_quality": "good",
                    "confidence_score": 0.9,
                }
            )
            return InferenceResponse(
                request_id=request.request_id,
                structured_output=perception,
                confidence=perception.confidence_score,
                latency_ms=1.0,
                provider_metadata=ProviderMetadata(
                    capability="meal_vision",
                    provider="stub",
                    model="stub-model",
                    endpoint="http://stub",
                ),
            )

    monkeypatch.setattr("dietary_guardian.agent.meal_analysis.vision_module.InferenceEngine", StubEngine)

    module = HawkerVisionModule(provider="qwen")
    image_input = ImageInput(
        source="upload",
        filename="char_kway_teow.webp",
        mime_type="image/webp",
        content=b"\x00\x01\x02\x03",
    )

    await module.analyze_dish(image_input)

    request = seen.get("request")
    assert request is not None
    request = cast(InferenceRequest, request)
    assert request.modality == InferenceModality.IMAGE
    assert request.payload.get("image_bytes") == image_input.content
    assert request.payload.get("image_mime_type") == image_input.mime_type

    get_settings.cache_clear()


@pytest.mark.anyio
async def test_binary_image_input_keeps_safe_clarification_when_inference_v2_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_USE_INFERENCE_ENGINE_V2", "false")
    get_settings.cache_clear()

    module = HawkerVisionModule(provider="test")
    image_input = ImageInput(
        source="upload",
        filename="hawker.jpg",
        mime_type="image/jpeg",
        content=b"\xff\xd8\xff",
    )

    result = await module.analyze_dish(image_input)

    assert result.needs_manual_review is False
    assert result.primary_state.identification_method == "AI_Flash"
    assert result.perception is not None
    assert result.perception.meal_detected is True
    assert result.primary_state.dish_name == "hawker"
    get_settings.cache_clear()
