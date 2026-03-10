"""Meal record access helpers shared by nutrition and recommendation logic."""

from __future__ import annotations

from dietary_guardian.domain.meals import MealNutritionProfile
from dietary_guardian.domain.meals.models import Ingredient, Nutrition
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord


def meal_display_name(record: MealRecognitionRecord) -> str:
    if record.enriched_event is not None and record.enriched_event.meal_name:
        return record.enriched_event.meal_name
    return record.meal_state.dish_name


def meal_nutrition(record: MealRecognitionRecord) -> Nutrition:
    if record.enriched_event is not None:
        return record.enriched_event.total_nutrition.to_legacy()
    return record.meal_state.nutrition


def meal_ingredients(record: MealRecognitionRecord) -> list[Ingredient]:
    if record.enriched_event is not None and record.enriched_event.normalized_items:
        return [
            Ingredient(
                name=item.canonical_name,
                amount_g=item.estimated_grams,
            )
            for item in record.enriched_event.normalized_items
        ]
    return list(record.meal_state.ingredients)


def meal_nutrition_profile(record: MealRecognitionRecord) -> MealNutritionProfile:
    if record.enriched_event is not None:
        return record.enriched_event.total_nutrition
    return MealNutritionProfile.from_legacy(record.meal_state.nutrition)


def meal_confidence(record: MealRecognitionRecord) -> float:
    if record.meal_perception is not None:
        return record.meal_perception.confidence_score
    return record.meal_state.confidence_score


def meal_identification_method(record: MealRecognitionRecord) -> str:
    return str(record.meal_state.identification_method)


def meal_risk_tags(record: MealRecognitionRecord) -> list[str]:
    if record.enriched_event is not None:
        return list(record.enriched_event.risk_tags)
    return []
