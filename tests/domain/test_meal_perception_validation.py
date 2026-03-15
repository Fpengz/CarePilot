"""Tests for MealPerception validation."""

from care_pilot.features.meals.domain.models import MealPerception


def test_meal_perception_accepts_image_quality_dict() -> None:
    perception = MealPerception.model_validate(
        {
            "meal_detected": True,
            "items": [],
            "uncertainties": [],
            "image_quality": {
                "clarity": "good",
                "lighting": "good",
                "angle": "good",
                "color_accuracy": "good",
            },
            "confidence_score": 0.9,
        }
    )

    assert perception.image_quality == "good"


def test_meal_perception_accepts_items_dict() -> None:
    perception = MealPerception.model_validate(
        {
            "meal_detected": True,
            "items": {
                "label": "Char Kway Teow",
                "candidate_aliases": ["Char Kway Teow"],
                "portion_estimate": {
                    "amount": 1.0,
                    "unit": "plate",
                    "confidence": 0.8,
                },
                "confidence": 0.9,
            },
            "uncertainties": [],
            "image_quality": "good",
            "confidence_score": 0.8,
        }
    )

    assert len(perception.items) == 1
    assert perception.items[0].label == "Char Kway Teow"


def test_meal_perception_accepts_confidence_score_string() -> None:
    perception = MealPerception.model_validate(
        {
            "meal_detected": True,
            "items": [],
            "uncertainties": [],
            "image_quality": "good",
            "confidence_score": "0.85",
        }
    )

    assert perception.confidence_score == 0.85


def test_meal_perception_accepts_candidate_aliases_string() -> None:
    perception = MealPerception.model_validate(
        {
            "meal_detected": True,
            "items": [
                {
                    "label": "Char Kway Teow",
                    "candidate_aliases": "Char Kway Teow",
                    "portion_estimate": {
                        "amount": 1.0,
                        "unit": "plate",
                        "confidence": 0.8,
                    },
                    "confidence": 0.9,
                }
            ],
            "uncertainties": [],
            "image_quality": "good",
            "confidence_score": 0.8,
        }
    )

    assert perception.items[0].candidate_aliases == ["Char Kway Teow"]


def test_meal_perception_accepts_name_field_and_quantity_portion() -> None:
    perception = MealPerception.model_validate(
        {
            "meal_detected": True,
            "items": [
                {
                    "name": "炒粿条",
                    "candidate_aliases": ["炒河粉", "福建炒面", "虾炒粿条"],
                    "portion_estimate": {
                        "quantity": "2-3 servings",
                        "unit": "servings",
                    },
                    "confidence": 0.95,
                }
            ],
            "uncertainties": [],
            "image_quality": "good",
            "confidence_score": 0.92,
        }
    )

    assert perception.items[0].label == "炒粿条"
    assert perception.items[0].portion_estimate.unit == "servings"
