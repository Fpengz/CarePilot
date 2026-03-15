"""Define emotion inference ports for the pipeline."""

from __future__ import annotations

from typing import Protocol

from care_pilot.agent.emotion.schemas import (
    EmotionContextFeatures,
    EmotionTextAgentInput,
    EmotionSpeechAgentInput,
    EmotionInferenceResult,
    EmotionRuntimeHealth,
    TextEmotionBranchResult,
    SpeechEmotionBranchResult,
    EmotionFusionOutput,
    FusionTrace,
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
    ) -> TextEmotionBranchResult: ...


class SpeechEmotionPort(Protocol):
    def predict(
        self,
        audio_bytes: bytes,
        *,
        transcript: str | None,
    ) -> SpeechEmotionBranchResult: ...


class ContextFeaturePort(Protocol):
    def extract(self, user_id: str | None) -> EmotionContextFeatures: ...


class FusionPort(Protocol):
    def predict(
        self,
        *,
        text_branch: TextEmotionBranchResult | None,
        speech_branch: SpeechEmotionBranchResult | None,
        context: EmotionContextFeatures,
    ) -> tuple[EmotionFusionOutput, FusionTrace]: ...


class EmotionInferencePort(Protocol):
    def infer_text(
        self, payload: EmotionTextAgentInput
    ) -> EmotionInferenceResult:
        """Infer emotion labels from text input."""

    def infer_speech(
        self, payload: EmotionSpeechAgentInput
    ) -> EmotionInferenceResult:
        """Infer emotion labels from speech/audio input."""

    def health(self) -> EmotionRuntimeHealth:
        """Return runtime health for the active emotion backend."""


__all__ = [
    "ASRPort",
    "TextEmotionPort",
    "SpeechEmotionPort",
    "ContextFeaturePort",
    "FusionPort",
    "EmotionInferencePort",
]
