"""
Define LLM runtime dataclasses and typing helpers.

This module contains shared dataclasses and type aliases used by the
LLM runtime and routing layers.
"""

from dataclasses import dataclass

from dietary_guardian.config.llm import (
    LLMCapability,
    LLMCapabilityTarget,
    LocalModelProfile,
    ModelProvider,
)


@dataclass(frozen=True)
class ResolvedModelRuntime:
    provider: str
    model_name: str
    capability: str | None = None
    base_url: str | None = None
    api_key: str | None = None


__all__ = [
    "LLMCapability",
    "LLMCapabilityTarget",
    "LocalModelProfile",
    "ModelProvider",
    "ResolvedModelRuntime",
]
