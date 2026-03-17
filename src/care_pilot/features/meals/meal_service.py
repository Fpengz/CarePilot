"""
Provide the meals feature entrypoint.

This module exposes the main business operations for meal workflows.
"""

from care_pilot.features.meals.domain.normalization import (
    build_meal_record,
    normalize_vision_result,
)
from care_pilot.features.meals.presenters.api import build_meal_analysis_output
from care_pilot.features.meals.use_cases import (
    MealCandidateInvalidStateError,
    MealCandidateNotFoundError,
    analyze_meal_upload,
    build_context_snapshot,
    confirm_meal_candidate,
    get_daily_summary_data,
    get_weekly_summary_data,
    list_meal_records_page,
    log_meal_analysis_completion,
)

__all__ = [
    "MealCandidateInvalidStateError",
    "MealCandidateNotFoundError",
    "analyze_meal_upload",
    "build_context_snapshot",
    "build_meal_analysis_output",
    "build_meal_record",
    "confirm_meal_candidate",
    "get_daily_summary_data",
    "get_weekly_summary_data",
    "list_meal_records_page",
    "log_meal_analysis_completion",
    "normalize_vision_result",
]
