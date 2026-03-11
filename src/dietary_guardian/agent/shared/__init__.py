"""Shared agent contracts and runtime helpers."""

from dietary_guardian.agent.dietary.agent import (
    AgentResponse,
    dietary_agent,
    get_model,
    process_meal_request,
)
from dietary_guardian.agent.shared.ai.engine import InferenceEngine, destination_ref
from dietary_guardian.agent.shared.base import AgentContext, AgentResult, BaseAgent
from dietary_guardian.agent.shared.registry import AgentRegistry, build_default_agent_registry

__all__ = [
    "AgentContext",
    "AgentRegistry",
    "AgentResponse",
    "AgentResult",
    "BaseAgent",
    "InferenceEngine",
    "build_default_agent_registry",
    "destination_ref",
    "dietary_agent",
    "get_model",
    "process_meal_request",
]
