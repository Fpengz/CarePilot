"""Orchestrate multimodal emotion inference."""

from __future__ import annotations

from dietary_guardian.agent.emotion.ports import ASRPort, FusionPort, SpeechEmotionPort, TextEmotionPort
from dietary_guardian.features.companion.core.health.emotion import (
    EmotionContextFeatures,
    EmotionFusionOutput,
    EmotionInferenceResult,
    EmotionSpeechBranch,
    EmotionTextBranch,
)


class EmotionPipeline:
    def __init__(
        self,
        *,
        asr: ASRPort,
        text: TextEmotionPort,
        speech: SpeechEmotionPort,
        fusion: FusionPort,
    ) -> None:
        self._asr = asr
        self._text = text
        self._speech = speech
        self._fusion = fusion

    def infer_text(
        self,
        *,
        text: str,
        language: str | None,
        context: EmotionContextFeatures,
    ) -> EmotionInferenceResult:
        text_scores, text_model_name, text_model_version = self._text.predict(text, language)
        fusion_label, product_state, confidence, logits = self._fusion.predict(
            text_scores=text_scores,
            speech_scores=None,
            context=context,
        )
        return EmotionInferenceResult(
            source_type="text",
            text_branch=EmotionTextBranch(
                transcript=text,
                model_name=text_model_name,
                model_version=text_model_version,
                scores=text_scores,
            ),
            speech_branch=None,
            context_features=context,
            fusion=EmotionFusionOutput(
                emotion_label=fusion_label,
                product_state=product_state,
                confidence=confidence,
                logits=logits,
            ),
        )

    def infer_speech(
        self,
        *,
        audio_bytes: bytes,
        filename: str | None,
        language: str | None,
        transcription: str | None,
        context: EmotionContextFeatures,
    ) -> EmotionInferenceResult:
        asr_transcript = self._asr.transcribe(audio_bytes, filename=filename, language=language)
        text_transcript = transcription or asr_transcript
        speech_scores, acoustic_summary, speech_model_name, speech_model_version = self._speech.predict(
            audio_bytes,
            transcript=asr_transcript,
        )
        text_scores, text_model_name, text_model_version = self._text.predict(text_transcript, language)
        fusion_label, product_state, confidence, logits = self._fusion.predict(
            text_scores=text_scores,
            speech_scores=speech_scores,
            context=context,
        )
        return EmotionInferenceResult(
            source_type="mixed",
            text_branch=EmotionTextBranch(
                transcript=text_transcript,
                model_name=text_model_name,
                model_version=text_model_version,
                scores=text_scores,
            ),
            speech_branch=EmotionSpeechBranch(
                transcript=asr_transcript,
                model_name=speech_model_name,
                model_version=speech_model_version,
                scores=speech_scores,
                acoustic_summary=acoustic_summary,
            ),
            context_features=context,
            fusion=EmotionFusionOutput(
                emotion_label=fusion_label,
                product_state=product_state,
                confidence=confidence,
                logits=logits,
            ),
        )
