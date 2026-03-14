"""Define emotion inference ports for the pipeline."""

from __future__ import annotations

from typing import Protocol

from dietary_guardian.agent.emotion.schemas import (
    EmotionContextFeatures,
    EmotionLabel,
    EmotionProductState,
    EmotionTextAgentInput,
    EmotionSpeechAgentInput,
    EmotionInferenceResult,
    EmotionRuntimeHealth,
)


class ASRPort(Protocol):
    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str | None,
        language: str | None,
    ) -> str: ...


class TextEmotionPort(Protocol):
    def predict(
        self,
        text: str,
        language: str | None,
    ) -> tuple[dict[EmotionLabel, float], str, str]: ...


class SpeechEmotionPort(Protocol):
    def predict(
        self,
        audio_bytes: bytes,
        *,
        transcript: str | None,
    ) -> tuple[dict[EmotionLabel, float], dict[str, float], str, str]: ...


class FusionPort(Protocol):
    def predict(
        self,
        *,
        text_scores: dict[EmotionLabel, float],
        speech_scores: dict[EmotionLabel, float] | None,
        context: EmotionContextFeatures,
    ) -> tuple[EmotionLabel, EmotionProductState, float, dict[EmotionLabel, float]]: ...


class EmotionInferencePort(Protocol):
    def infer_text(self, payload: EmotionTextAgentInput) -> EmotionInferenceResult:
        """Infer emotion labels from text input."""

    def infer_speech(self, payload: EmotionSpeechAgentInput) -> EmotionInferenceResult:
        """Infer emotion labels from speech/audio input."""

    def health(self) -> EmotionRuntimeHealth:
        """Return runtime health for the active emotion backend."""


__all__ = [
    "ASRPort",
    "TextEmotionPort",
    "SpeechEmotionPort",
    "FusionPort",
    "EmotionInferencePort",
]
