"""Agent I/O schemas for recommendation synthesis — pure domain contracts."""

from __future__ import annotations

from pydantic import BaseModel

from dietary_guardian.domain.health.models import ClinicalProfileSnapshot, HealthProfileRecord
from dietary_guardian.domain.identity.models import UserProfile
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord
from dietary_guardian.domain.recommendations.models import DailyAgentRecommendation


class RecommendationAgentInput(BaseModel):
    """Typed context for generating a daily recommendation bundle."""

    user_id: str
    health_profile: HealthProfileRecord
    user_profile: UserProfile
    meal_history: list[MealRecognitionRecord]
    clinical_snapshot: ClinicalProfileSnapshot | None = None


class RecommendationAgentOutput(BaseModel):
    """Standardized recommendation agent output wrapper."""

    recommendation: DailyAgentRecommendation


__all__ = ["RecommendationAgentInput", "RecommendationAgentOutput"]
