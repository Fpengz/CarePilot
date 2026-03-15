"""
Define emotion-related health models.

This module re-exports models from the agent layer for compatibility.
"""

from __future__ import annotations

from dietary_guardian.agent.emotion.schemas import (
    EmotionConfidenceBand,
    EmotionContextFeatures,
    EmotionEvidence,
    EmotionFusionOutput,
    EmotionInferenceResult,
    EmotionLabel,
    EmotionProductState,
    EmotionRuntimeHealth,
    SpeechEmotionBranchResult,
    TextEmotionBranchResult,
)

__all__ = [
    "EmotionConfidenceBand",
    "EmotionContextFeatures",
    "EmotionEvidence",
    "EmotionFusionOutput",
    "EmotionInferenceResult",
    "EmotionLabel",
    "EmotionProductState",
    "EmotionRuntimeHealth",
    "SpeechEmotionBranchResult",
    "TextEmotionBranchResult",
]
