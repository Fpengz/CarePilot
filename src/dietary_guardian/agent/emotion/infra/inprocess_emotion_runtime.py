"""Infrastructure support for inprocess emotion runtime."""

from __future__ import annotations

from dietary_guardian.features.companion.engagement.emotion.ports import (
    EmotionInferencePort,
    SpeechEmotionInput,
    TextEmotionInput,
)
from dietary_guardian.agent.emotion.infra.config import EmotionRuntimeConfig
from dietary_guardian.agent.emotion.infra.emotion_engine import EmotionEngine
from dietary_guardian.agent.emotion.infra.model_loader import EmotionModelLoader
from dietary_guardian.agent.emotion.infra.speech_emotion import SpeechEmotionClassifier
from dietary_guardian.agent.emotion.infra.text_emotion import TextEmotionClassifier
from dietary_guardian.features.companion.core.health.emotion import EmotionInferenceResult, EmotionRuntimeHealth


class InProcessEmotionRuntime(EmotionInferencePort):
    def __init__(self, config: EmotionRuntimeConfig) -> None:
        text_classifier = TextEmotionClassifier()
        speech_classifier = SpeechEmotionClassifier(text_classifier=text_classifier)
        loader = EmotionModelLoader(config)
        self._engine = EmotionEngine(
            config=config,
            loader=loader,
            text_classifier=text_classifier,
            speech_classifier=speech_classifier,
        )

    def infer_text(self, payload: TextEmotionInput) -> EmotionInferenceResult:
        return self._engine.infer_text(text=payload.text, language=payload.language)

    def infer_speech(self, payload: SpeechEmotionInput) -> EmotionInferenceResult:
        return self._engine.infer_speech(
            audio_bytes=payload.audio_bytes,
            filename=payload.filename,
            content_type=payload.content_type,
            transcription=payload.transcription,
            language=payload.language,
        )

    def health(self) -> EmotionRuntimeHealth:
        return self._engine.health()
