"""Metric trend calculations for biomarker, meal, and adherence history."""

from .trend_analysis import (
    adherence_rate_points,
    biomarker_points,
    build_metric_trend,
    meal_calorie_points,
)

__all__ = [
    "adherence_rate_points",
    "biomarker_points",
    "build_metric_trend",
    "meal_calorie_points",
]
