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


class EmotionEvidence(BaseModel):
    label: EmotionLabel
    score: float = Field(ge=0.0, le=1.0)


class EmotionInferenceResult(BaseModel):
    source_type: Literal["text", "speech", "mixed"]
    emotion: EmotionLabel
    score: float = Field(ge=0.0, le=1.0)
    confidence_band: EmotionConfidenceBand
    model_name: str
    model_version: str
    evidence: list[EmotionEvidence] = Field(default_factory=list)
    transcription: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmotionRuntimeHealth(BaseModel):
    status: Literal["ready", "degraded"]
    model_cache_ready: bool
    source_commit: str
    detail: str | None = None
