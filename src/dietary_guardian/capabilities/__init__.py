"""Canonical agent exports for reasoning units, contracts, and execution surfaces."""

from dietary_guardian.capabilities.base import AgentContext, AgentResult, BaseAgent
from dietary_guardian.capabilities.dietary import (
    AgentResponse,
    dietary_agent,
    get_model,
    process_meal_request,
)
from dietary_guardian.capabilities.emotion import (
    EmotionAgent,
    EmotionAgentDisabledError,
    EmotionSpeechDisabledError,
)
from dietary_guardian.infrastructure.ai.engine import InferenceEngine, destination_ref
from dietary_guardian.capabilities.meal_analysis import MealAnalysisAgent
from dietary_guardian.capabilities.recommendation import RecommendationAgent
from dietary_guardian.capabilities.registry import AgentRegistry, build_default_agent_registry
from dietary_guardian.capabilities.vision import HawkerVisionModule

__all__ = [
    "AgentRegistry",
    "AgentContext",
    "AgentResponse",
    "AgentResult",
    "BaseAgent",
    "EmotionAgent",
    "EmotionAgentDisabledError",
    "EmotionSpeechDisabledError",
    "HawkerVisionModule",
    "InferenceEngine",
    "MealAnalysisAgent",
    "RecommendationAgent",
    "build_default_agent_registry",
    "destination_ref",
    "dietary_agent",
    "get_model",
    "process_meal_request",
]
