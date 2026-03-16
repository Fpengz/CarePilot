from io import BytesIO
from typing import Any, cast

import pytest
from PIL import Image

from care_pilot.agent.meal_analysis import HawkerVisionModule
from care_pilot.agent.runtime.inference_types import (
    InferenceModality,
    InferenceRequest,
    InferenceResponse,
    ProviderMetadata,
)
from care_pilot.config.app import get_settings
from care_pilot.features.meals.domain.models import ImageInput, MealPerception


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
                            "portion_estimate": {
                                "amount": 1.0,
                                "unit": "plate",
                                "confidence": 0.9,
                            },
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

    monkeypatch.setattr(
        "care_pilot.agent.meal_analysis.vision_module.InferenceEngine",
        StubEngine,
    )

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
async def test_webp_input_converts_to_jpeg_for_inference_engine(
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
                            "portion_estimate": {
                                "amount": 1.0,
                                "unit": "plate",
                                "confidence": 0.9,
                            },
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

    monkeypatch.setattr(
        "care_pilot.agent.meal_analysis.vision_module.InferenceEngine",
        StubEngine,
    )

    buffer = BytesIO()
    Image.new("RGB", (2, 2), color=(120, 60, 30)).save(buffer, format="WEBP")
    webp_bytes = buffer.getvalue()

    module = HawkerVisionModule(provider="qwen")
    image_input = ImageInput(
        source="upload",
        filename="char_kway_teow.webp",
        mime_type="image/webp",
        content=webp_bytes,
    )

    await module.analyze_dish(image_input)

    request = seen.get("request")
    assert request is not None
    request = cast(InferenceRequest, request)
    assert request.modality == InferenceModality.IMAGE
    assert request.payload.get("image_mime_type") == "image/jpeg"
    assert isinstance(request.payload.get("image_bytes"), (bytes, bytearray))
    assert request.payload.get("image_bytes", b"")[:3] == b"\xff\xd8\xff"

    get_settings.cache_clear()


@pytest.mark.anyio
async def test_debug_logging_emits_inference_payload_details(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_USE_INFERENCE_ENGINE_V2", "true")
    get_settings.cache_clear()

    class StubStrategy:
        async def run(self, request):  # noqa: ANN001
            perception = MealPerception.model_validate(
                {
                    "meal_detected": True,
                    "items": [
                        {
                            "label": "Char Kway Teow",
                            "candidate_aliases": ["Char Kway Teow"],
                            "portion_estimate": {
                                "amount": 1.0,
                                "unit": "plate",
                                "confidence": 0.9,
                            },
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

        def supports(self, modality):  # noqa: ANN001
            del modality
            return True

    caplog.set_level("DEBUG")
    module = HawkerVisionModule(provider="qwen")
    cast(Any, module.inference_engine).strategy = StubStrategy()
    image_input = ImageInput(
        source="upload",
        filename="char_kway_teow.webp",
        mime_type="image/webp",
        content=b"\x00\x01\x02\x03",
    )

    await module.analyze_dish(image_input)

    messages = [record.message for record in caplog.records]
    assert any("hawker_vision_inference_payload" in msg for msg in messages)
    assert any("inference_engine_payload" in msg for msg in messages)

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
