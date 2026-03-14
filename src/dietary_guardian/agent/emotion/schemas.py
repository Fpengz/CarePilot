"""
Define emotion agent input/output schemas.

This module contains the typed request and response contracts used by
emotion inference workflows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

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


class EmotionTextBranch(BaseModel):
    transcript: str
    model_name: str
    model_version: str
    scores: dict[EmotionLabel, float]


class EmotionSpeechBranch(BaseModel):
    transcript: str | None = None
    model_name: str
    model_version: str
    scores: dict[EmotionLabel, float]
    acoustic_summary: dict[str, float] = Field(default_factory=dict)


class EmotionContextFeatures(BaseModel):
    recent_labels: list[EmotionLabel] = Field(default_factory=list)
    trend: Literal["worsening", "stable", "improving"]


class EmotionFusionOutput(BaseModel):
    emotion_label: EmotionLabel
    product_state: EmotionProductState
    confidence: float = Field(ge=0.0, le=1.0)
    logits: dict[EmotionLabel, float] = Field(default_factory=dict)


class EmotionInferenceResult(BaseModel):
    source_type: Literal["text", "speech", "mixed"]
    text_branch: EmotionTextBranch | None = None
    speech_branch: EmotionSpeechBranch | None = None
    context_features: EmotionContextFeatures
    fusion: EmotionFusionOutput
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmotionRuntimeHealth(BaseModel):
    status: Literal["ready", "degraded", "disabled"]
    model_cache_ready: bool
    source_commit: str
    detail: str | None = None


class EmotionTextAgentInput(BaseModel):
    """Text payload for emotion inference."""

    text: str
    language: str | None = None
    context: EmotionContextFeatures | None = None


class EmotionSpeechAgentInput(BaseModel):
    """Speech payload for emotion inference."""

    audio_bytes: bytes
    filename: str | None = None
    content_type: str | None = None
    transcription: str | None = None
    language: str | None = None
    context: EmotionContextFeatures | None = None


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
    "EmotionTextBranch",
    "EmotionSpeechBranch",
    "EmotionContextFeatures",
    "EmotionFusionOutput",
    "EmotionInferenceResult",
    "EmotionRuntimeHealth",
]
