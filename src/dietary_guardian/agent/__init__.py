"""Canonical bounded agent exports with lazy resolution."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MAP = {
    "AgentContext": ("dietary_guardian.agent.core", "AgentContext"),
    "AgentRegistry": ("dietary_guardian.agent.core", "AgentRegistry"),
    "AgentResponse": ("dietary_guardian.agent.dietary", "AgentResponse"),
    "AgentResult": ("dietary_guardian.agent.core", "AgentResult"),
    "BaseAgent": ("dietary_guardian.agent.core", "BaseAgent"),
    "EmotionAgent": ("dietary_guardian.agent.emotion", "EmotionAgent"),
    "EmotionAgentDisabledError": ("dietary_guardian.agent.emotion", "EmotionAgentDisabledError"),
    "EmotionSpeechDisabledError": ("dietary_guardian.agent.emotion", "EmotionSpeechDisabledError"),
    "HawkerVisionModule": ("dietary_guardian.agent.meal_analysis", "HawkerVisionModule"),
    "InferenceEngine": ("dietary_guardian.agent.runtime", "InferenceEngine"),
    "MealAnalysisAgent": ("dietary_guardian.agent.meal_analysis", "MealAnalysisAgent"),
    "RecommendationAgent": ("dietary_guardian.agent.recommendation", "RecommendationAgent"),
    "build_default_agent_registry": ("dietary_guardian.agent.core", "build_default_agent_registry"),
    "destination_ref": ("dietary_guardian.agent.runtime", "destination_ref"),
    "dietary_agent": ("dietary_guardian.agent.dietary", "dietary_agent"),
    "get_model": ("dietary_guardian.agent.dietary.agent", "get_model"),
    "process_meal_request": ("dietary_guardian.agent.dietary.agent", "process_meal_request"),
}

__all__ = sorted(_EXPORT_MAP)


def __getattr__(name: str) -> Any:
    if name not in _EXPORT_MAP:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    module_name, attr_name = _EXPORT_MAP[name]
    module = import_module(module_name)
    return getattr(module, attr_name)
