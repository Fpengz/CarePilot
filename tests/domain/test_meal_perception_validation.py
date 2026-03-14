"""Tests for MealPerception validation."""

from dietary_guardian.features.meals.domain.models import MealPerception


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
