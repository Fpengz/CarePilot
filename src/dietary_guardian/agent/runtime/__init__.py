"""Shared runtime plumbing for agent inference and model routing."""

from dietary_guardian.agent.runtime.inference_engine import (
    CloudStrategy,
    InferenceEngine,
    LocalStrategy,
    ProviderStrategy,
    TestStrategy,
    destination_ref,
)
from dietary_guardian.agent.runtime.inference_types import (
    InferenceHealth,
    InferenceModality,
    InferenceRequest,
    InferenceResponse,
    ModalityCapabilityProfile,
    ProviderMetadata,
)
from dietary_guardian.agent.runtime.llm_factory import LLMFactory, ModelType
from dietary_guardian.agent.runtime.llm_types import (
    LLMCapability,
    LLMCapabilityTarget,
    LocalModelProfile,
    ModelProvider,
    ResolvedModelRuntime,
)

__all__ = [
    "CloudStrategy",
    "InferenceEngine",
    "InferenceHealth",
    "InferenceModality",
    "InferenceRequest",
    "InferenceResponse",
    "LLMCapability",
    "LLMCapabilityTarget",
    "LLMFactory",
    "LocalModelProfile",
    "LocalStrategy",
    "ModalityCapabilityProfile",
    "ModelProvider",
    "ModelType",
    "ProviderMetadata",
    "ProviderStrategy",
    "ResolvedModelRuntime",
    "TestStrategy",
    "destination_ref",
]
