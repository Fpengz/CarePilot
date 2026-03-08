from __future__ import annotations

from dietary_guardian.infrastructure.emotion.audio_preprocessor import preprocess_audio
from dietary_guardian.infrastructure.emotion.config import EmotionRuntimeConfig
from dietary_guardian.infrastructure.emotion.model_loader import EmotionModelLoader
from dietary_guardian.infrastructure.emotion.speech_emotion import SpeechEmotionClassifier
from dietary_guardian.infrastructure.emotion.text_emotion import TextEmotionClassifier
from dietary_guardian.infrastructure.emotion.text_preprocessor import normalize_text
from dietary_guardian.models.emotion import (
    EmotionConfidenceBand,
    EmotionEvidence,
    EmotionInferenceResult,
    EmotionLabel,
    EmotionRuntimeHealth,
)
from typing import Literal


class EmotionEngine:
    def __init__(
        self,
        *,
        config: EmotionRuntimeConfig,
        loader: EmotionModelLoader,
        text_classifier: TextEmotionClassifier,
        speech_classifier: SpeechEmotionClassifier,
    ) -> None:
        self._config = config
        self._loader = loader
        self._text_classifier = text_classifier
        self._speech_classifier = speech_classifier

    def infer_text(self, *, text: str, language: str | None = None) -> EmotionInferenceResult:
        del language
        normalized = normalize_text(text)
        if not normalized:
            raise ValueError("text is empty")
        self._loader.ensure_loaded()
        scores = self._text_classifier.predict_scores(normalized)
        return self._build_result(source_type="text", scores=scores, transcription=None)

    def infer_speech(
        self,
        *,
        audio_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
        transcription: str | None = None,
        language: str | None = None,
    ) -> EmotionInferenceResult:
        del filename, language
        payload = preprocess_audio(audio_bytes, content_type=content_type)
        self._loader.ensure_loaded()
        scores, derived_transcription = self._speech_classifier.predict_scores(
            audio_bytes=payload,
            transcription=normalize_text(transcription) if transcription else None,
        )
        return self._build_result(
            source_type="speech",
            scores=scores,
            transcription=derived_transcription,
        )

    def health(self) -> EmotionRuntimeHealth:
        return EmotionRuntimeHealth(
            status="ready" if self._loader.is_ready else "degraded",
            model_cache_ready=self._loader.is_ready,
            source_commit=self._config.source_commit,
            detail=None if self._loader.is_ready else "models not warmed",
        )

    def _build_result(
        self,
        *,
        source_type: Literal["text", "speech", "mixed"],
        scores: dict[EmotionLabel, float],
        transcription: str | None,
    ) -> EmotionInferenceResult:
        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_label, top_score = ordered[0]
        return EmotionInferenceResult(
            source_type=source_type,
            emotion=top_label,
            score=top_score,
            confidence_band=self._confidence_band(top_score),
            model_name=self._loader.model_name,
            model_version=self._loader.model_version,
            evidence=[EmotionEvidence(label=label, score=score) for label, score in ordered],
            transcription=transcription,
        )

    @staticmethod
    def _confidence_band(score: float) -> EmotionConfidenceBand:
        if score >= 0.75:
            return EmotionConfidenceBand.HIGH
        if score >= 0.5:
            return EmotionConfidenceBand.MEDIUM
        return EmotionConfidenceBand.LOW
