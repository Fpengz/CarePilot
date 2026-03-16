"""Meals feature use case entrypoints."""

from .analyze_meal import analyze_meal_upload, log_meal_analysis_completion
from .records import list_meal_records_page, MealRecordsPage
from .summaries import get_daily_summary_data, get_weekly_summary_data, MealWeeklySummaryData
from .confirm_meal import (
    confirm_meal_candidate,
    MealCandidateInvalidStateError,
    MealCandidateNotFoundError,
)

__all__ = [
    "analyze_meal_upload",
    "log_meal_analysis_completion",
    "list_meal_records_page",
    "MealRecordsPage",
    "get_daily_summary_data",
    "get_weekly_summary_data",
    "MealWeeklySummaryData",
    "confirm_meal_candidate",
    "MealCandidateInvalidStateError",
    "MealCandidateNotFoundError",
]
