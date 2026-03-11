"""API meal service — thin shim.

Canonical logic lives in ``dietary_guardian.features.meals.service``.
"""

from __future__ import annotations

from dietary_guardian.features.meals.service import (  # noqa: F401
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
