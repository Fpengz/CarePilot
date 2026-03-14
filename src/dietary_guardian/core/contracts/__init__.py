"""Package exports for contracts with lazy resolution."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MAP = {
    "SCHEMA_VERSION_V1": ("dietary_guardian.core.contracts.agent_envelopes", "SCHEMA_VERSION_V1"),
    "AgentContract": ("dietary_guardian.platform.observability.workflows.domain.models", "AgentContract"),
    "AgentExecutionTrace": ("dietary_guardian.core.contracts.agent_envelopes", "AgentExecutionTrace"),
    "AgentHandoff": ("dietary_guardian.core.contracts.agent_envelopes", "AgentHandoff"),
    "AgentInputEnvelope": ("dietary_guardian.core.contracts.agent_envelopes", "AgentInputEnvelope"),
    "AgentOutputEnvelope": ("dietary_guardian.core.contracts.agent_envelopes", "AgentOutputEnvelope"),
    "AuditRecord": ("dietary_guardian.core.contracts.agent_envelopes", "AuditRecord"),
    "CaptureEnvelope": ("dietary_guardian.core.contracts.agent_envelopes", "CaptureEnvelope"),
    "DomainDecision": ("dietary_guardian.core.contracts.agent_envelopes", "DomainDecision"),
    "EmotionConfidenceBand": ("dietary_guardian.agent.emotion.schemas", "EmotionConfidenceBand"),
    "EmotionEvidence": ("dietary_guardian.agent.emotion.schemas", "EmotionEvidence"),
    "EmotionInferenceResult": ("dietary_guardian.agent.emotion.schemas", "EmotionInferenceResult"),
    "EmotionLabel": ("dietary_guardian.agent.emotion.schemas", "EmotionLabel"),
    "EmotionRuntimeHealth": ("dietary_guardian.agent.emotion.schemas", "EmotionRuntimeHealth"),
    "EngagementMetrics": ("dietary_guardian.features.companion.core.health.analytics", "EngagementMetrics"),
    "EvidenceItem": ("dietary_guardian.core.contracts.agent_envelopes", "EvidenceItem"),
    "InferenceHealth": ("dietary_guardian.agent.runtime.inference_types", "InferenceHealth"),
    "InferenceModality": ("dietary_guardian.agent.runtime.inference_types", "InferenceModality"),
    "InferenceRequest": ("dietary_guardian.agent.runtime.inference_types", "InferenceRequest"),
    "InferenceResponse": ("dietary_guardian.agent.runtime.inference_types", "InferenceResponse"),
    "PresentationMessage": ("dietary_guardian.core.contracts.agent_envelopes", "PresentationMessage"),
    "ProviderMetadata": ("dietary_guardian.agent.runtime.inference_types", "ProviderMetadata"),
    "ToolExecutionError": ("dietary_guardian.platform.observability.tooling.domain.models", "ToolExecutionError"),
    "ToolExecutionResult": ("dietary_guardian.platform.observability.tooling.domain.models", "ToolExecutionResult"),
    "ToolPolicyContext": ("dietary_guardian.platform.observability.tooling.domain.models", "ToolPolicyContext"),
    "ToolSensitivity": ("dietary_guardian.platform.observability.tooling.domain.models", "ToolSensitivity"),
    "ToolSideEffect": ("dietary_guardian.platform.observability.tooling.domain.models", "ToolSideEffect"),
    "ToolSpec": ("dietary_guardian.platform.observability.tooling.domain.models", "ToolSpec"),
    "WorkflowRuntimeContract": ("dietary_guardian.platform.observability.workflows.domain.models", "WorkflowRuntimeContract"),
}

__all__ = sorted(_EXPORT_MAP)


def __getattr__(name: str) -> Any:
    if name not in _EXPORT_MAP:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    module_name, attr_name = _EXPORT_MAP[name]
    module = import_module(module_name)
    return getattr(module, attr_name)
