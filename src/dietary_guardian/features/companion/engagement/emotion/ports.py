"""
Define emotion engagement ports.

This module declares the interfaces used to request emotion inference
within engagement workflows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dietary_guardian.features.companion.core.health.emotion import (
    EmotionContextFeatures,
    EmotionInferenceResult,
    EmotionRuntimeHealth,
)


@dataclass(frozen=True, slots=True)
class TextEmotionInput:
    text: str
    language: str | None = None
    context: EmotionContextFeatures | None = None


@dataclass(frozen=True, slots=True)
class SpeechEmotionInput:
    audio_bytes: bytes
    filename: str | None = None
    content_type: str | None = None
    transcription: str | None = None
    language: str | None = None
    context: EmotionContextFeatures | None = None


class EmotionInferencePort(Protocol):
    def infer_text(self, payload: TextEmotionInput) -> EmotionInferenceResult:
        """Infer emotion labels from text input."""

    def infer_speech(self, payload: SpeechEmotionInput) -> EmotionInferenceResult:
        """Infer emotion labels from speech/audio input."""

    def health(self) -> EmotionRuntimeHealth:
        """Return runtime health for the active emotion backend."""
