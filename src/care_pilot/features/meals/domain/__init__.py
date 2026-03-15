"""Package exports for meals."""

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
from .models import (
    EnrichedMealEvent,
    GlycemicIndexLevel,
    ImageInput,
    Ingredient,
    LocalizationDetails,
    MealEvent,
    MealNutritionProfile,
    MealPerception,
    MealPortionEstimate,
    MealState,
    NormalizedMealItem,
    Nutrition,
    PerceivedMealItem,
    PortionReference,
    PortionSize,
    RawFoodSourceRecord,
    SafetyAnalysis,
    VisionResult,
)
from .nutrition_models import DailyNutritionSummary, NutritionInsight, NutritionTotals
from .recognition import MealRecognitionRecord
from .weekly_summary import build_weekly_nutrition_summary

__all__ = [
    "DailyNutritionSummary",
    "EnrichedMealEvent",
    "GlycemicIndexLevel",
    "ImageInput",
    "Ingredient",
    "LocalizationDetails",
    "MealEvent",
    "MealNutritionProfile",
    "MealPerception",
    "MealPortionEstimate",
    "MealState",
    "MealRecognitionRecord",
    "NormalizedMealItem",
    "Nutrition",
    "NutritionInsight",
    "NutritionTotals",
    "PerceivedMealItem",
    "PortionReference",
    "PortionSize",
    "RawFoodSourceRecord",
    "SafetyAnalysis",
    "VisionResult",
    "build_daily_nutrition_summary",
    "build_weekly_nutrition_summary",
    "meal_confidence",
    "meal_display_name",
    "meal_identification_method",
    "meal_ingredients",
    "meal_nutrition",
    "meal_nutrition_profile",
    "meal_risk_tags",
]
