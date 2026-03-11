"""Meals feature business entrypoint."""

from dietary_guardian.features.meals.api_service import (
    analyze_meal,
    get_daily_summary,
    get_weekly_summary,
    list_meal_records,
)
from dietary_guardian.features.meals.presenter import build_meal_analysis_output
from dietary_guardian.features.meals.use_cases import build_meal_record, normalize_vision_result

__all__ = [
    "analyze_meal",
    "build_meal_analysis_output",
    "build_meal_record",
    "get_daily_summary",
    "get_weekly_summary",
    "list_meal_records",
    "normalize_vision_result",
]
