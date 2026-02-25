import pytest

from dietary_guardian.agents.hawker_vision import HawkerVisionModule
from dietary_guardian.config.settings import get_settings
from dietary_guardian.models.meal import ImageInput


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

    assert result.needs_manual_review is True
    assert result.primary_state.identification_method == "User_Manual"
    assert result.primary_state.dish_name == "Clarification Required"
    assert "cannot process raw image bytes" in result.raw_ai_output.lower()


@pytest.mark.anyio
async def test_binary_image_input_keeps_safe_clarification_when_inference_v2_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("USE_INFERENCE_ENGINE_V2", "false")
    get_settings.cache_clear()

    module = HawkerVisionModule(provider="test")
    image_input = ImageInput(
        source="upload",
        filename="hawker.jpg",
        mime_type="image/jpeg",
        content=b"\xff\xd8\xff",
    )

    result = await module.analyze_dish(image_input)

    assert result.needs_manual_review is True
    assert result.primary_state.identification_method == "User_Manual"
    assert result.primary_state.dish_name == "Clarification Required"
    assert "cannot process raw image bytes" in result.raw_ai_output.lower()
    get_settings.cache_clear()
