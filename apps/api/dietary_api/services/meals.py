"""API meal service — thin shim.

All logic lives in ``dietary_guardian.application.meals.api_service``.
"""

from __future__ import annotations

from dietary_guardian.application.meals.api_service import (  # noqa: F401
    HawkerVisionModule,
    analyze_meal,
    get_daily_summary,
    get_weekly_summary,
    list_meal_records,
)

__all__ = [
    "HawkerVisionModule",
    "analyze_meal",
    "get_daily_summary",
    "get_weekly_summary",
    "list_meal_records",
]
