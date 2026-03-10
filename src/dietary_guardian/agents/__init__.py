"""Canonical agent exports for reasoning units, contracts, and execution surfaces."""

from dietary_guardian.agents.base import AgentContext, AgentResult, BaseAgent
from dietary_guardian.agents.dietary import (
    AgentResponse,
    dietary_agent,
    get_model,
    process_meal_request,
)
from dietary_guardian.agents.emotion import (
    EmotionAgent,
    EmotionAgentDisabledError,
    EmotionSpeechDisabledError,
)
from dietary_guardian.agents.executor import InferenceEngine, destination_ref
from dietary_guardian.agents.meal_analysis import MealAnalysisAgent
from dietary_guardian.agents.recommendation import RecommendationAgent
from dietary_guardian.agents.registry import AgentRegistry, build_default_agent_registry
from dietary_guardian.agents.vision import HawkerVisionModule

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
