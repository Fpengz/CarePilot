"""
Define emotion agent input/output schemas.

This module contains the typed request and response contracts used by
emotion inference workflows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EmotionLabel(StrEnum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FRUSTRATED = "frustrated"
    ANXIOUS = "anxious"
    NEUTRAL = "neutral"
    CONFUSED = "confused"
    FEARFUL = "fearful"


class EmotionConfidenceBand(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EmotionProductState(StrEnum):
    STABLE = "stable"
    NEEDS_REASSURANCE = "needs_reassurance"
    CONFUSED = "confused"
    DISTRESSED = "distressed"
    URGENT_REVIEW = "urgent_review"


class EmotionEvidence(BaseModel):
    label: EmotionLabel
    score: float = Field(ge=0.0, le=1.0)


class TextEmotionBranchResult(BaseModel):
    transcript_or_text: str
    emotion_scores: dict[EmotionLabel, float]
    predicted_emotion: EmotionLabel
    confidence: float
    model_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpeechEmotionBranchResult(BaseModel):
    raw_audio_reference: str | None = None
    transcription: str | None = None
    acoustic_scores: dict[str, float] = Field(default_factory=dict)
    predicted_emotion: EmotionLabel
    emotion_scores: dict[EmotionLabel, float]
    confidence: float
    asr_metadata: dict[str, Any] = Field(default_factory=dict)
    model_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmotionContextFeatures(BaseModel):
    recent_labels: list[EmotionLabel] = Field(default_factory=list)
    trend: Literal["worsening", "stable", "improving"]
    recent_product_states: list[EmotionProductState] = Field(default_factory=list)


class FusionTrace(BaseModel):
    fusion_inputs: dict[str, Any]
    weighting_strategy: str
    conflict_resolution: str | None = None
    final_decision_reason: str


class EmotionFusionOutput(BaseModel):
    emotion_label: EmotionLabel
    product_state: EmotionProductState
    confidence: float = Field(ge=0.0, le=1.0)
    logits: dict[EmotionLabel, float] = Field(default_factory=dict)


class EmotionInferenceResult(BaseModel):
    source_type: Literal["text", "speech", "mixed"]
    final_emotion: EmotionLabel
    product_state: EmotionProductState
    confidence: float
    text_branch: TextEmotionBranchResult | None = None
    speech_branch: SpeechEmotionBranchResult | None = None
    context_features: EmotionContextFeatures
    fusion_method: str
    model_metadata: dict[str, str] = Field(default_factory=dict)
    trace: FusionTrace
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EmotionRuntimeHealth(BaseModel):
    status: Literal["ready", "degraded", "disabled"]
    model_cache_ready: bool
    source_commit: str
    detail: str | None = None


class EmotionTextAgentInput(BaseModel):
    """Text payload for emotion inference."""

    text: str
    language: str | None = None
    user_id: str | None = None


class EmotionSpeechAgentInput(BaseModel):
    """Speech payload for emotion inference."""

    audio_bytes: bytes
    filename: str | None = None
    content_type: str | None = None
    transcription: str | None = None
    language: str | None = None
    user_id: str | None = None


class EmotionAgentOutput(BaseModel):
    """Standardized emotion agent output wrapper."""

    inference: EmotionInferenceResult


# Aliases for compatibility
SpeechEmotionInput = EmotionSpeechAgentInput
TextEmotionInput = EmotionTextAgentInput

__all__ = [
    "EmotionAgentOutput",
    "EmotionSpeechAgentInput",
    "EmotionTextAgentInput",
    "SpeechEmotionInput",
    "TextEmotionInput",
    "EmotionLabel",
    "EmotionConfidenceBand",
    "EmotionProductState",
    "EmotionEvidence",
    "TextEmotionBranchResult",
    "SpeechEmotionBranchResult",
    "EmotionContextFeatures",
    "FusionTrace",
    "EmotionFusionOutput",
    "EmotionInferenceResult",
    "EmotionRuntimeHealth",
]
