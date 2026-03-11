"""Agent I/O schemas for emotion inference — pure domain contracts."""

from __future__ import annotations

from pydantic import BaseModel

from dietary_guardian.domain.health.emotion import EmotionInferenceResult


class EmotionTextAgentInput(BaseModel):
    """Text payload for emotion inference."""

    text: str
    language: str | None = None


class EmotionSpeechAgentInput(BaseModel):
    """Speech payload for emotion inference."""

    audio_bytes: bytes
    filename: str | None = None
    content_type: str | None = None
    transcription: str | None = None
    language: str | None = None


class EmotionAgentOutput(BaseModel):
    """Standardized emotion agent output wrapper."""

    inference: EmotionInferenceResult


__all__ = ["EmotionAgentOutput", "EmotionSpeechAgentInput", "EmotionTextAgentInput"]
