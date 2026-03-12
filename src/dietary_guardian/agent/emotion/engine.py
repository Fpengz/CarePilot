"""
Execute emotion inference workflows.

This module defines the core emotion inference engine that coordinates
text and audio classification pipelines.
"""

from __future__ import annotations

from typing import Literal

from dietary_guardian.agent.emotion.audio_preprocessor import preprocess_audio
from dietary_guardian.agent.emotion.config import EmotionRuntimeConfig
from dietary_guardian.agent.emotion.model_loader import EmotionModelLoader
from dietary_guardian.agent.emotion.speech_classifier import SpeechEmotionClassifier
from dietary_guardian.agent.emotion.text_classifier import TextEmotionClassifier
from dietary_guardian.agent.emotion.text_preprocessor import normalize_text
from dietary_guardian.features.companion.core.health.emotion import (
    EmotionContextFeatures,
    EmotionFusionOutput,
    EmotionInferenceResult,
    EmotionLabel,
    EmotionProductState,
    EmotionRuntimeHealth,
    EmotionSpeechBranch,
    EmotionTextBranch,
)


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
        return self._build_result(source_type="text", scores=scores, transcription=normalized)

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
        fusion = EmotionFusionOutput(
            emotion_label=top_label,
            product_state=_product_state_for_label(top_label),
            confidence=top_score,
            logits={label: score for label, score in ordered},
        )
        text_branch = None
        speech_branch = None
        if source_type == "text":
            text_branch = EmotionTextBranch(
                transcript=transcription or "",
                model_name=self._loader.model_name,
                model_version=self._loader.model_version,
                scores=scores,
            )
        else:
            speech_branch = EmotionSpeechBranch(
                transcript=transcription,
                model_name=self._loader.model_name,
                model_version=self._loader.model_version,
                scores=scores,
                acoustic_summary={},
            )
        return EmotionInferenceResult(
            source_type=source_type,
            text_branch=text_branch,
            speech_branch=speech_branch,
            context_features=EmotionContextFeatures(recent_labels=[], trend="stable"),
            fusion=fusion,
        )


def _product_state_for_label(label: EmotionLabel) -> EmotionProductState:
    if label in {EmotionLabel.ANGRY, EmotionLabel.FRUSTRATED}:
        return EmotionProductState.DISTRESSED
    if label in {EmotionLabel.ANXIOUS, EmotionLabel.FEARFUL, EmotionLabel.SAD}:
        return EmotionProductState.NEEDS_REASSURANCE
    if label == EmotionLabel.CONFUSED:
        return EmotionProductState.CONFUSED
    return EmotionProductState.STABLE
