"""Tests for meal normalization."""

from dietary_guardian.application.meals.use_cases import normalize_vision_result
from dietary_guardian.domain.meals import MealPerception
from dietary_guardian.domain.recommendations.models import CanonicalFoodRecord
from dietary_guardian.domain.meals.models import MealState, Nutrition, VisionResult


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

    def list_canonical_foods(self, *, locale: str, slot: str | None = None, limit: int = 100) -> list[CanonicalFoodRecord]:
        records = [record for record in self._records if record.locale == locale and record.active]
        if slot is not None:
            records = [record for record in records if record.slot == slot]
        return records[:limit]


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


def test_normalize_vision_result_uses_component_refinement_for_ambiguous_label() -> None:
    store = _StubFoodStore(
        CanonicalFoodRecord(
            food_id="ckt",
            title="Char Kway Teow",
            aliases=["Char Kway Teow"],
            aliases_normalized=["char kway teow"],
            slot="lunch",
            venue_type="hawker",
            cuisine_tags=["local"],
            ingredient_tags=["egg", "cockles", "kway teow"],
            preparation_tags=["fried", "noodles"],
            nutrition=Nutrition(calories=700, carbs_g=80, sugar_g=8, protein_g=20, fat_g=30, sodium_mg=1200),
        ),
        CanonicalFoodRecord(
            food_id="soup",
            title="Kway Teow Soup",
            aliases=["Kway Teow Soup"],
            aliases_normalized=["kway teow soup"],
            slot="lunch",
            venue_type="hawker",
            cuisine_tags=["local"],
            ingredient_tags=["fish cake", "soup", "kway teow"],
            preparation_tags=["soup", "noodles"],
            nutrition=Nutrition(calories=350, carbs_g=50, sugar_g=2, protein_g=12, fat_g=6, sodium_mg=650),
        ),
    )
    vision_result = VisionResult(
        primary_state=MealState(
            dish_name="Kway Teow",
            confidence_score=0.82,
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
                        "label": "Kway Teow",
                        "candidate_aliases": ["Char Kway Teow", "Kway Teow Soup"],
                        "portion_estimate": {"amount": 1.0, "unit": "plate", "confidence": 0.8},
                        "preparation": "fried",
                        "confidence": 0.85,
                    }
                ],
                "image_quality": "good",
                "confidence_score": 0.82,
            }
        ),
    )

    normalized = normalize_vision_result(vision_result=vision_result, food_store=store, locale="en-SG")

    assert normalized.enriched_event is not None
    assert normalized.enriched_event.normalized_items[0].canonical_food_id == "ckt"
    assert normalized.enriched_event.normalized_items[0].match_confidence >= 0.85
    assert normalized.primary_state.dish_name == "Char Kway Teow"


def test_normalize_vision_result_marks_ambiguous_component_mismatch_for_manual_review() -> None:
    store = _StubFoodStore(
        CanonicalFoodRecord(
            food_id="laksa",
            title="Laksa",
            aliases=["Laksa"],
            aliases_normalized=["laksa"],
            slot="lunch",
            venue_type="hawker",
            cuisine_tags=["local"],
            ingredient_tags=["coconut", "prawn", "bee hoon"],
            preparation_tags=["soup", "noodles"],
            nutrition=Nutrition(calories=600, carbs_g=55, sugar_g=5, protein_g=18, fat_g=30, sodium_mg=1200),
        ),
    )
    vision_result = VisionResult(
        primary_state=MealState(
            dish_name="Laksa",
            confidence_score=0.78,
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
                        "portion_estimate": {"amount": 1.0, "unit": "bowl", "confidence": 0.8},
                        "preparation": "fried",
                        "confidence": 0.79,
                    }
                ],
                "uncertainties": [],
                "image_quality": "good",
                "confidence_score": 0.78,
            }
        ),
    )

    normalized = normalize_vision_result(vision_result=vision_result, food_store=store, locale="en-SG")

    assert normalized.enriched_event is not None
    assert normalized.enriched_event.needs_manual_review is True
    assert "component_mismatch" in normalized.enriched_event.risk_tags
