from datetime import datetime

from dietary_guardian.models.meal import MealState, Nutrition
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.infrastructure.persistence import SQLiteRepository


def test_meal_record_round_trip(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "records.db"))
    record = MealRecognitionRecord(
        id="m1",
        user_id="u1",
        captured_at=datetime(2026, 2, 24, 12, 0),
        source="upload",
        meal_state=MealState(
            dish_name="Laksa",
            confidence_score=0.9,
            identification_method="AI_Flash",
            ingredients=[],
            nutrition=Nutrition(calories=550, carbs_g=60, sugar_g=6, protein_g=18, fat_g=25, sodium_mg=1400),
        ),
        multi_item_count=2,
    )
    repo.save_meal_record(record)

    rows = repo.list_meal_records("u1")
    assert len(rows) == 1
    assert rows[0].meal_state.dish_name == "Laksa"
    assert rows[0].multi_item_count == 2
