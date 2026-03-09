from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from dietary_guardian.models.emotion import EmotionConfidenceBand, EmotionLabel


class EmotionTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    language: str | None = None


class EmotionEvidenceResponse(BaseModel):
    label: EmotionLabel
    score: float = Field(ge=0.0, le=1.0)


class EmotionObservationResponse(BaseModel):
    source_type: Literal["text", "speech", "mixed"]
    emotion: EmotionLabel
    score: float = Field(ge=0.0, le=1.0)
    confidence_band: EmotionConfidenceBand
    model_name: str
    model_version: str
    evidence: list[EmotionEvidenceResponse] = Field(default_factory=list)
    transcription: str | None = None
    created_at: datetime
    request_id: str | None = None
    correlation_id: str | None = None


class EmotionInferenceResponse(BaseModel):
    observation: EmotionObservationResponse


class EmotionHealthResponse(BaseModel):
    status: Literal["ready", "degraded"]
    model_cache_ready: bool
    source_commit: str
    detail: str | None = None
