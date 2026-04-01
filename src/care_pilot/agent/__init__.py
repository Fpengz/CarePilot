"""Canonical bounded agent exports with lazy resolution."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MAP = {
    "AgentContext": ("care_pilot.agent.core", "AgentContext"),
    "AgentRegistry": ("care_pilot.agent.core", "AgentRegistry"),
    "AgentResult": ("care_pilot.agent.core", "AgentResult"),
    "BaseAgent": ("care_pilot.agent.core", "BaseAgent"),
    "DietaryAgentInput": (
        "care_pilot.agent.dietary.schemas",
        "DietaryAgentInput",
    ),
    "DietaryAgentOutput": (
        "care_pilot.agent.dietary.schemas",
        "DietaryAgentOutput",
    ),
    "analyze_dietary_request": (
        "care_pilot.agent.dietary.agent",
        "analyze_dietary_request",
    ),
    "MealAnalysisAgentInput": (
        "care_pilot.agent.meal_analysis.schemas",
        "MealAnalysisAgentInput",
    ),
    "MealAnalysisAgentOutput": (
        "care_pilot.agent.meal_analysis.schemas",
        "MealAnalysisAgentOutput",
    ),
    "analyze_meal_perception": (
        "care_pilot.agent.meal_analysis.agent",
        "analyze_meal_perception",
    ),
    "arbitrate_meal_label": (
        "care_pilot.agent.meal_analysis.arbitration",
        "arbitrate_meal_label",
    ),
    "EmotionAgent": ("care_pilot.agent.emotion", "EmotionAgent"),
    "RecommendationAgent": (
        "care_pilot.agent.recommendation",
        "RecommendationAgent",
    ),
    "InferenceEngine": ("care_pilot.agent.runtime", "InferenceEngine"),
    "LLMFactory": ("care_pilot.agent.runtime", "LLMFactory"),
}

__all__ = sorted(_EXPORT_MAP)


def __getattr__(name: str) -> Any:
    if name not in _EXPORT_MAP:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    module_name, attr_name = _EXPORT_MAP[name]
    module = import_module(module_name)
    return getattr(module, attr_name)
