"""Meals feature use case entrypoints."""

from .analyze_meal import analyze_meal_upload, log_meal_analysis_completion
from .confirm_meal import (
    MealCandidateInvalidStateError,
    MealCandidateNotFoundError,
    confirm_meal_candidate,
)
from .records import MealRecordsPage, list_meal_records_page
from .summaries import MealWeeklySummaryData, get_daily_summary_data, get_weekly_summary_data

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
