"""Meals feature business entrypoint.

Keep this module free of FastAPI/transport dependencies. Transport-level
wrappers belong under `apps/api/...` and should call into this module.
"""

from dietary_guardian.features.meals.presenter import build_meal_analysis_output
from dietary_guardian.features.meals.use_cases import build_meal_record, normalize_vision_result

__all__ = [
    "build_meal_analysis_output",
    "build_meal_record",
    "normalize_vision_result",
]
