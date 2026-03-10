"""Typed contracts for canonical agent inputs and outputs."""

from dietary_guardian.capabilities.schemas.dietary import DietaryAgentInput
from dietary_guardian.capabilities.schemas.emotion import (
    EmotionAgentOutput,
    EmotionSpeechAgentInput,
    EmotionTextAgentInput,
)
from dietary_guardian.capabilities.schemas.meal_analysis import (
    MealAnalysisAgentInput,
    MealAnalysisAgentOutput,
)
from dietary_guardian.capabilities.schemas.recommendation import (
    RecommendationAgentInput,
    RecommendationAgentOutput,
)

__all__ = [
    "DietaryAgentInput",
    "EmotionAgentOutput",
    "EmotionSpeechAgentInput",
    "EmotionTextAgentInput",
    "MealAnalysisAgentInput",
    "MealAnalysisAgentOutput",
    "RecommendationAgentInput",
    "RecommendationAgentOutput",
]
