"""Tests for meal record persistence."""

from datetime import datetime

from dietary_guardian.domain.meals import EnrichedMealEvent, MealNutritionProfile, MealPerception
from dietary_guardian.infrastructure.persistence import SQLiteRepository
from dietary_guardian.models.meal import MealState, Nutrition
from dietary_guardian.models.meal_record import MealRecognitionRecord


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
        meal_perception=MealPerception.model_validate(
            {
                "meal_detected": True,
                "items": [
                    {
                        "label": "Laksa",
                        "candidate_aliases": ["Laksa"],
                        "portion_estimate": {"amount": 1.0, "unit": "bowl", "confidence": 0.9},
                        "confidence": 0.9,
                    }
                ],
                "uncertainties": [],
                "image_quality": "good",
                "confidence_score": 0.9,
            }
        ),
        enriched_event=EnrichedMealEvent(
            meal_name="Laksa",
            normalized_items=[],
            total_nutrition=MealNutritionProfile(
                calories=550,
                carbs_g=60,
                sugar_g=6,
                protein_g=18,
                fat_g=25,
                sodium_mg=1400,
                fiber_g=0,
            ),
            risk_tags=["high_sodium"],
        ),
        multi_item_count=2,
    )
    repo.save_meal_record(record)

    rows = repo.list_meal_records("u1")
    assert len(rows) == 1
    assert rows[0].meal_state.dish_name == "Laksa"
    assert rows[0].meal_perception is not None
    assert rows[0].enriched_event is not None
    assert rows[0].multi_item_count == 2
