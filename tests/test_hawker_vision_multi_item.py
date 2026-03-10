"""Tests for hawker vision multi item."""

import pytest

from dietary_guardian.agents.vision import HawkerVisionModule
from dietary_guardian.models.meal import ImageInput


@pytest.mark.anyio
async def test_analyze_and_record_uses_multi_item_metadata() -> None:
    module = HawkerVisionModule(provider="test")
    image_input = ImageInput(
        source="upload",
        filename="rice_fish_veg.jpg",
        mime_type="image/jpeg",
        content=b"abc",
        metadata={"multi_item_count": "3"},
    )
    result, record = await module.analyze_and_record(image_input, user_id="u1")

    assert result.needs_manual_review is True
    assert record.multi_item_count == 3
    assert record.user_id == "u1"
