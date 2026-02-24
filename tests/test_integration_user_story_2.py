import pytest

from dietary_guardian.agents.hawker_vision import HawkerVisionModule
from dietary_guardian.models.meal import ImageInput
from dietary_guardian.services.repository import SQLiteRepository


@pytest.mark.anyio
async def test_user_story_2_image_to_structured_record(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "int2.db"))
    module = HawkerVisionModule(provider="test")
    image_input = ImageInput(
        source="upload",
        filename="rice_fish_veg.jpg",
        mime_type="image/jpeg",
        content=b"abc",
        metadata={"multi_item_count": "3"},
    )
    _result, record = await module.analyze_and_record(image_input, user_id="u1")
    repo.save_meal_record(record)

    rows = repo.list_meal_records("u1")
    assert len(rows) == 1
    assert rows[0].multi_item_count == 3
