"""Nutrition domain services and meal record access helpers."""

from .daily_summary import build_daily_nutrition_summary
from .meal_record_accessors import (
    meal_confidence,
    meal_display_name,
    meal_identification_method,
    meal_ingredients,
    meal_nutrition,
    meal_nutrition_profile,
    meal_risk_tags,
)
from .models import DailyNutritionSummary, NutritionInsight, NutritionTotals
from .weekly_summary import build_weekly_nutrition_summary

__all__ = [
    "build_daily_nutrition_summary",
    "build_weekly_nutrition_summary",
    "DailyNutritionSummary",
    "NutritionInsight",
    "NutritionTotals",
    "meal_confidence",
    "meal_display_name",
    "meal_identification_method",
    "meal_ingredients",
    "meal_nutrition",
    "meal_nutrition_profile",
    "meal_risk_tags",
]
