"""Orchestrate multimodal emotion inference."""

from __future__ import annotations

from dietary_guardian.features.companion.emotion.ports import (
    ASRPort,
    FusionPort,
    SpeechEmotionPort,
    TextEmotionPort,
    ContextFeaturePort,
)
from dietary_guardian.agent.emotion.schemas import (
    EmotionInferenceResult,
)


class EmotionPipeline:
    def __init__(
        self,
        *,
        asr: ASRPort,
        text: TextEmotionPort,
        speech: SpeechEmotionPort,
        context: ContextFeaturePort,
        fusion: FusionPort,
    ) -> None:
        self._asr = asr
        self._text = text
        self._speech = speech
        self._context = context
        self._fusion = fusion

    def infer_text(
        self,
        *,
        text: str,
        language: str | None,
        user_id: str | None,
    ) -> EmotionInferenceResult:
        context_features = self._context.extract(user_id)
        text_branch_result = self._text.predict(text, language)
        fusion_output, trace = self._fusion.predict(
            text_branch=text_branch_result,
            speech_branch=None,
            context=context_features,
        )
        return EmotionInferenceResult(
            source_type="text",
            final_emotion=fusion_output.emotion_label,
            product_state=fusion_output.product_state,
            confidence=fusion_output.confidence,
            text_branch=text_branch_result,
            speech_branch=None,
            context_features=context_features,
            fusion_method="hf-text-classification-head",
            model_metadata={
                "text_model": text_branch_result.model_name,
            },
            trace=trace,
        )

    def infer_speech(
        self,
        *,
        audio_bytes: bytes,
        filename: str | None,
        language: str | None,
        transcription: str | None,
        user_id: str | None,
    ) -> EmotionInferenceResult:
        context_features = self._context.extract(user_id)
        asr_transcript = transcription or self._asr.transcribe(audio_bytes, filename=filename, language=language)
        
        speech_branch_result = self._speech.predict(
            audio_bytes,
            transcript=asr_transcript,
        )
        text_branch_result = self._text.predict(asr_transcript, language)
        
        fusion_output, trace = self._fusion.predict(
            text_branch=text_branch_result,
            speech_branch=speech_branch_result,
            context=context_features,
        )
        
        return EmotionInferenceResult(
            source_type="mixed",
            final_emotion=fusion_output.emotion_label,
            product_state=fusion_output.product_state,
            confidence=fusion_output.confidence,
            text_branch=text_branch_result,
            speech_branch=speech_branch_result,
            context_features=context_features,
            fusion_method="hf-text-classification-head",
            model_metadata={
                "text_model": text_branch_result.model_name,
                "speech_model": speech_branch_result.model_name,
            },
            trace=trace,
        )
