"""Canonical emotion agent built on the emotion inference runtime port."""

from __future__ import annotations

from dietary_guardian.agents.base import AgentContext, AgentResult, BaseAgent
from dietary_guardian.agents.schemas import (
    EmotionAgentOutput,
    EmotionSpeechAgentInput,
    EmotionTextAgentInput,
)
from dietary_guardian.application.emotion.ports import (
    EmotionInferencePort,
    SpeechEmotionInput,
    TextEmotionInput,
)
from dietary_guardian.application.emotion.use_cases import (
    EmotionInferenceTimeoutError,
    infer_speech_emotion,
    infer_text_emotion,
)
from dietary_guardian.models.emotion import EmotionRuntimeHealth


class EmotionAgentDisabledError(RuntimeError):
    """Raised when emotion inference is disabled via feature flag."""


class EmotionSpeechDisabledError(RuntimeError):
    """Raised when speech emotion inference is disabled via feature flag."""


class EmotionAgent(BaseAgent[EmotionTextAgentInput | EmotionSpeechAgentInput, EmotionAgentOutput]):
    """Canonical agent facade for text and speech emotion inference."""

    name = "emotion_agent"

    def __init__(
        self,
        *,
        runtime: EmotionInferencePort,
        inference_enabled: bool,
        speech_enabled: bool,
        request_timeout_seconds: float,
    ) -> None:
        self._runtime = runtime
        self._inference_enabled = inference_enabled
        self._speech_enabled = speech_enabled
        self._request_timeout_seconds = request_timeout_seconds

    async def run(
        self,
        input_data: EmotionTextAgentInput | EmotionSpeechAgentInput,
        context: AgentContext,
    ) -> AgentResult[EmotionAgentOutput]:
        del context
        if isinstance(input_data, EmotionTextAgentInput):
            inference = self.infer_text(text=input_data.text, language=input_data.language)
        else:
            inference = self.infer_speech(
                audio_bytes=input_data.audio_bytes,
                filename=input_data.filename,
                content_type=input_data.content_type,
                transcription=input_data.transcription,
                language=input_data.language,
            )
        return AgentResult(
            success=True,
            agent_name=self.name,
            output=EmotionAgentOutput(inference=inference),
            confidence=float(inference.score),
            raw=inference.model_dump(mode="json"),
        )

    def infer_text(
        self,
        *,
        text: str,
        language: str | None = None,
    ):
        if not self._inference_enabled:
            raise EmotionAgentDisabledError("emotion inference is disabled")
        return infer_text_emotion(
            port=self._runtime,
            payload=TextEmotionInput(text=text, language=language),
            timeout_seconds=self._request_timeout_seconds,
        )

    def infer_speech(
        self,
        *,
        audio_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
        transcription: str | None = None,
        language: str | None = None,
    ):
        if not self._inference_enabled:
            raise EmotionAgentDisabledError("emotion inference is disabled")
        if not self._speech_enabled:
            raise EmotionSpeechDisabledError("speech emotion inference is disabled")
        return infer_speech_emotion(
            port=self._runtime,
            payload=SpeechEmotionInput(
                audio_bytes=audio_bytes,
                filename=filename,
                content_type=content_type,
                transcription=transcription,
                language=language,
            ),
            timeout_seconds=self._request_timeout_seconds,
        )

    def health(self) -> EmotionRuntimeHealth:
        return self._runtime.health()

    @property
    def timeout_error_type(self) -> type[EmotionInferenceTimeoutError]:
        return EmotionInferenceTimeoutError
