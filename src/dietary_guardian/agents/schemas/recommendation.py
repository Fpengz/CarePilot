"""Input and output contracts for recommendation synthesis agents."""

from pydantic import BaseModel

from dietary_guardian.domain.health.models import ClinicalProfileSnapshot, HealthProfileRecord
from dietary_guardian.domain.identity.models import UserProfile
from dietary_guardian.domain.recommendations.models import DailyAgentRecommendation
from dietary_guardian.models.meal_record import MealRecognitionRecord


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
