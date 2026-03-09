from dietary_guardian.application.meals.use_cases import normalize_vision_result
from dietary_guardian.models.canonical_food import CanonicalFoodRecord
from dietary_guardian.domain.meals import MealPerception
from dietary_guardian.models.meal import MealState, Nutrition, VisionResult


class _StubFoodStore:
    def __init__(self, *records: CanonicalFoodRecord) -> None:
        self._records = list(records)

    def find_food_by_name(self, *, locale: str, name: str) -> CanonicalFoodRecord | None:
        for record in self._records:
            if record.locale != locale:
                continue
            names = [record.title, *record.aliases]
            if name in names:
                return record
        return None


def _food(*, food_id: str, title: str) -> CanonicalFoodRecord:
    return CanonicalFoodRecord(
        food_id=food_id,
        title=title,
        aliases=[title],
        aliases_normalized=[title.lower()],
        slot="lunch",
        venue_type="hawker",
        cuisine_tags=["local"],
        preparation_tags=["prepared"],
        nutrition=Nutrition(calories=100, carbs_g=10, sugar_g=1, protein_g=2, fat_g=3, sodium_mg=120),
    )


def test_normalize_vision_result_preserves_multi_item_meal_name() -> None:
    store = _StubFoodStore(
        _food(food_id="laksa", title="Laksa"),
        _food(food_id="barley-drink", title="Barley Drink"),
    )
    vision_result = VisionResult(
        primary_state=MealState(
            dish_name="Laksa",
            confidence_score=0.9,
            identification_method="AI_Flash",
            ingredients=[],
            nutrition=Nutrition(calories=0, carbs_g=0, sugar_g=0, protein_g=0, fat_g=0, sodium_mg=0),
        ),
        raw_ai_output="{}",
        perception=MealPerception.model_validate(
            {
                "meal_detected": True,
                "items": [
                    {
                        "label": "Laksa",
                        "candidate_aliases": ["Laksa"],
                        "portion_estimate": {"amount": 1.0, "unit": "bowl", "confidence": 0.9},
                        "confidence": 0.95,
                    },
                    {
                        "label": "Barley Drink",
                        "candidate_aliases": ["Barley Drink"],
                        "portion_estimate": {"amount": 1.0, "unit": "glass", "confidence": 0.85},
                        "confidence": 0.9,
                    },
                ],
                "image_quality": "good",
                "confidence_score": 0.92,
            }
        ),
    )

    normalized = normalize_vision_result(vision_result=vision_result, food_store=store, locale="en-SG")

    assert normalized.enriched_event is not None
    assert normalized.enriched_event.meal_name == "Laksa + Barley Drink"
    assert normalized.primary_state.dish_name == "Laksa + Barley Drink"
    assert normalized.enriched_event.summary == "Laksa + Barley Drink with 2 detected item(s)"
