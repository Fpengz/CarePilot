"""Shared agent contracts and runtime helpers."""

from dietary_guardian.agent.shared.ai.engine import InferenceEngine, destination_ref
from dietary_guardian.agent.shared.base import AgentContext, AgentResult, BaseAgent
from dietary_guardian.agent.shared.registry import AgentRegistry, build_default_agent_registry

__all__ = [
    "AgentContext",
    "AgentRegistry",
    "AgentResult",
    "BaseAgent",
    "InferenceEngine",
    "build_default_agent_registry",
    "destination_ref",
]
