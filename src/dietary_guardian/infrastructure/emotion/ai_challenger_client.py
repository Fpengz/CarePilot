from __future__ import annotations

from dietary_guardian.application.emotion.ports import EmotionInferencePort, SpeechEmotionInput, TextEmotionInput
from dietary_guardian.models.emotion import EmotionInferenceResult, EmotionRuntimeHealth


class AiChallengerHttpClient(EmotionInferencePort):
    """Sidecar compatibility client placeholder for future fallback transport."""

    def infer_text(self, payload: TextEmotionInput) -> EmotionInferenceResult:
        del payload
        raise NotImplementedError("sidecar runtime is not enabled in this phase")

    def infer_speech(self, payload: SpeechEmotionInput) -> EmotionInferenceResult:
        del payload
        raise NotImplementedError("sidecar runtime is not enabled in this phase")

    def health(self) -> EmotionRuntimeHealth:
        raise NotImplementedError("sidecar runtime is not enabled in this phase")

