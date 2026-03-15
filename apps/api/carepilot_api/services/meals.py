"""API meal service — thin shim.

Canonical logic lives in ``care_pilot.features.meals.api_service``.
"""

from __future__ import annotations

from care_pilot.agent.meal_analysis.vision_module import HawkerVisionModule
from care_pilot.features.meals.service import (  # noqa: F401
    analyze_meal,
    get_daily_summary,
    get_weekly_summary,
    list_meal_records,
)

__all__ = [
    "analyze_meal",
    "get_daily_summary",
    "get_weekly_summary",
    "list_meal_records",
    "HawkerVisionModule",
]
