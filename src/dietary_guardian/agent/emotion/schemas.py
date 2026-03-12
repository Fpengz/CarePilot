"""
Define emotion agent input/output schemas.

This module contains the typed request and response contracts used by
emotion inference workflows.
"""

from __future__ import annotations

from pydantic import BaseModel

from dietary_guardian.features.companion.core.health.emotion import (
    EmotionContextFeatures,
    EmotionInferenceResult,
)


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


__all__ = ["EmotionAgentOutput", "EmotionSpeechAgentInput", "EmotionTextAgentInput"]
