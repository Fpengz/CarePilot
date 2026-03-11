"""API meal service — thin shim.

Canonical logic lives in ``dietary_guardian.features.meals.api_service``.
"""

from __future__ import annotations

from dietary_guardian.agent.vision.hawker_vision import HawkerVisionModule
from dietary_guardian.features.meals.service import (  # noqa: F401
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
