"""Canonical agent exports for dietary, vision, and execution surfaces."""

from dietary_guardian.agents.dietary import AgentResponse, dietary_agent, get_model, process_meal_request
from dietary_guardian.agents.executor import InferenceEngine, destination_ref
from dietary_guardian.agents.registry import AgentRegistry, build_default_agent_registry
from dietary_guardian.agents.vision import HawkerVisionModule

__all__ = [
    "AgentRegistry",
    "AgentResponse",
    "HawkerVisionModule",
    "InferenceEngine",
    "build_default_agent_registry",
    "destination_ref",
    "dietary_agent",
    "get_model",
    "process_meal_request",
]
