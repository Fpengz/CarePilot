"""Package exports for contracts with lazy resolution."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MAP = {
    "SCHEMA_VERSION_V1": (
        "care_pilot.core.contracts.agent_envelopes",
        "SCHEMA_VERSION_V1",
    ),
    "AgentContract": (
        "care_pilot.platform.observability.workflows.domain.models",
        "AgentContract",
    ),
    "AgentExecutionTrace": (
        "care_pilot.core.contracts.agent_envelopes",
        "AgentExecutionTrace",
    ),
    "AgentHandoff": (
        "care_pilot.core.contracts.agent_envelopes",
        "AgentHandoff",
    ),
    "AgentInputEnvelope": (
        "care_pilot.core.contracts.agent_envelopes",
        "AgentInputEnvelope",
    ),
    "AgentOutputEnvelope": (
        "care_pilot.core.contracts.agent_envelopes",
        "AgentOutputEnvelope",
    ),
    "AuditRecord": (
        "care_pilot.core.contracts.agent_envelopes",
        "AuditRecord",
    ),
    "CaptureEnvelope": (
        "care_pilot.core.contracts.agent_envelopes",
        "CaptureEnvelope",
    ),
    "DomainDecision": (
        "care_pilot.core.contracts.agent_envelopes",
        "DomainDecision",
    ),
    "EmotionConfidenceBand": (
        "care_pilot.agent.emotion.schemas",
        "EmotionConfidenceBand",
    ),
    "EmotionEvidence": ("care_pilot.agent.emotion.schemas", "EmotionEvidence"),
    "EmotionInferenceResult": (
        "care_pilot.agent.emotion.schemas",
        "EmotionInferenceResult",
    ),
    "EmotionLabel": ("care_pilot.agent.emotion.schemas", "EmotionLabel"),
    "EmotionRuntimeHealth": (
        "care_pilot.agent.emotion.schemas",
        "EmotionRuntimeHealth",
    ),
    "EngagementMetrics": (
        "care_pilot.features.companion.core.health.analytics",
        "EngagementMetrics",
    ),
    "EvidenceItem": (
        "care_pilot.core.contracts.agent_envelopes",
        "EvidenceItem",
    ),
    "InferenceHealth": (
        "care_pilot.agent.runtime.inference_types",
        "InferenceHealth",
    ),
    "InferenceModality": (
        "care_pilot.agent.runtime.inference_types",
        "InferenceModality",
    ),
    "InferenceRequest": (
        "care_pilot.agent.runtime.inference_types",
        "InferenceRequest",
    ),
    "InferenceResponse": (
        "care_pilot.agent.runtime.inference_types",
        "InferenceResponse",
    ),
    "PresentationMessage": (
        "care_pilot.core.contracts.agent_envelopes",
        "PresentationMessage",
    ),
    "ProviderMetadata": (
        "care_pilot.agent.runtime.inference_types",
        "ProviderMetadata",
    ),
    "ToolExecutionError": (
        "care_pilot.platform.observability.tooling.domain.models",
        "ToolExecutionError",
    ),
    "ToolExecutionResult": (
        "care_pilot.platform.observability.tooling.domain.models",
        "ToolExecutionResult",
    ),
    "ToolPolicyContext": (
        "care_pilot.platform.observability.tooling.domain.models",
        "ToolPolicyContext",
    ),
    "ToolSensitivity": (
        "care_pilot.platform.observability.tooling.domain.models",
        "ToolSensitivity",
    ),
    "ToolSideEffect": (
        "care_pilot.platform.observability.tooling.domain.models",
        "ToolSideEffect",
    ),
    "ToolSpec": (
        "care_pilot.platform.observability.tooling.domain.models",
        "ToolSpec",
    ),
    "WorkflowRuntimeContract": (
        "care_pilot.platform.observability.workflows.domain.models",
        "WorkflowRuntimeContract",
    ),
}

__all__ = sorted(_EXPORT_MAP)


def __getattr__(name: str) -> Any:
    if name not in _EXPORT_MAP:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    module_name, attr_name = _EXPORT_MAP[name]
    module = import_module(module_name)
    return getattr(module, attr_name)
