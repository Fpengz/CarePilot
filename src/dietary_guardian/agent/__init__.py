"""Canonical bounded agent exports with lazy resolution."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MAP = {
    "AgentContext": ("dietary_guardian.agent.core", "AgentContext"),
    "AgentRegistry": ("dietary_guardian.agent.core", "AgentRegistry"),
    "AgentResult": ("dietary_guardian.agent.core", "AgentResult"),
    "BaseAgent": ("dietary_guardian.agent.core", "BaseAgent"),
    "DietaryAgentInput": ("dietary_guardian.agent.dietary.schemas", "DietaryAgentInput"),
    "DietaryAgentOutput": ("dietary_guardian.agent.dietary.schemas", "DietaryAgentOutput"),
    "analyze_dietary_request": ("dietary_guardian.agent.dietary.agent", "analyze_dietary_request"),
    "MealAnalysisAgentInput": ("dietary_guardian.agent.meal_analysis.schemas", "MealAnalysisAgentInput"),
    "MealAnalysisAgentOutput": ("dietary_guardian.agent.meal_analysis.schemas", "MealAnalysisAgentOutput"),
    "analyze_meal_perception": ("dietary_guardian.agent.meal_analysis.meal_perception_agent", "analyze_meal_perception"),
    "arbitrate_meal_label": ("dietary_guardian.agent.meal_analysis.arbitration", "arbitrate_meal_label"),
    "EmotionAgent": ("dietary_guardian.agent.emotion", "EmotionAgent"),
    "RecommendationAgent": ("dietary_guardian.agent.recommendation", "RecommendationAgent"),
    "InferenceEngine": ("dietary_guardian.agent.runtime", "InferenceEngine"),
    "LLMFactory": ("dietary_guardian.agent.runtime", "LLMFactory"),
}

__all__ = sorted(_EXPORT_MAP)


def __getattr__(name: str) -> Any:
    if name not in _EXPORT_MAP:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    module_name, attr_name = _EXPORT_MAP[name]
    module = import_module(module_name)
    return getattr(module, attr_name)
