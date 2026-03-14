"""Define meal analysis agent contracts.

The meal-analysis feature owns the canonical domain models (MealPerception, etc.).
The agent layer re-exports and wraps those models for inference contracts.
"""

from __future__ import annotations

from pydantic import BaseModel

from dietary_guardian.features.meals.domain.models import (
    ImageQuality,
    MealPerception,
    MealPortionEstimate,
    PerceivedMealItem,
)

class MealAnalysisAgentInput(BaseModel):
    """Generic input for meal analysis requests."""

    image_bytes: bytes | None = None
    image_mime_type: str | None = None
    text_context: str | None = None
    user_id: str | None = None


class MealAnalysisAgentOutput(BaseModel):
    """Structured output from the meal analysis agent."""

    perception: MealPerception
    raw_output: str
    latency_ms: float = 0.0


__all__ = [
    "ImageQuality",
    "MealAnalysisAgentInput",
    "MealAnalysisAgentOutput",
    "MealPerception",
    "MealPortionEstimate",
    "PerceivedMealItem",
]
