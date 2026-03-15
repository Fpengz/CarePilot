"""HF speech emotion adapter."""

from __future__ import annotations

import io
import re

import numpy as np
import soundfile as sf
from transformers import pipeline

from care_pilot.features.companion.emotion.ports import SpeechEmotionPort
from care_pilot.agent.emotion.schemas import (
    EmotionLabel,
    SpeechEmotionBranchResult,
)
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)

_LABEL_MAP = {
    "happy": EmotionLabel.HAPPY,
    "joy": EmotionLabel.HAPPY,
    "sad": EmotionLabel.SAD,
    "sadness": EmotionLabel.SAD,
    "anger": EmotionLabel.ANGRY,
    "angry": EmotionLabel.ANGRY,
    "frustration": EmotionLabel.FRUSTRATED,
    "anxious": EmotionLabel.ANXIOUS,
    "anxiety": EmotionLabel.ANXIOUS,
    "fear": EmotionLabel.FEARFUL,
    "fearful": EmotionLabel.FEARFUL,
    "neutral": EmotionLabel.NEUTRAL,
    "confused": EmotionLabel.CONFUSED,
}


def _safe_preview(text: str | None, *, limit: int = 160) -> str | None:
    if not text:
        return None
    preview = text[:limit].replace("\n", " ")
    preview = re.sub(r"[0-9]", "x", preview)
    preview = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[redacted-email]", preview)
    return preview


class HFSpeechEmotion(SpeechEmotionPort):
    def __init__(self, model_id: str, device: str) -> None:
        self._model_id = model_id
        self._device = 0 if device == "cuda" else -1
        self._pipeline = None

    def _ensure_pipeline(self) -> None:
        if self._pipeline is not None:
            return
        self._pipeline = pipeline(
            "audio-classification",
            model=self._model_id,
            device=self._device,
            return_all_scores=True,
        )

    def predict(
        self,
        audio_bytes: bytes,
        *,
        transcript: str | None,
    ) -> SpeechEmotionBranchResult:
        data, sample_rate = sf.read(io.BytesIO(audio_bytes))
        if isinstance(data, np.ndarray) and data.ndim > 1:
            data = np.mean(data, axis=1)
        audio_array = data.astype(np.float32)
        duration_sec = float(len(audio_array) / sample_rate) if sample_rate else 0.0
        rms = float(np.sqrt(np.mean(np.square(audio_array)))) if len(audio_array) else 0.0

        self._ensure_pipeline()
        assert self._pipeline is not None
        logger.info(
            "emotion_speech_request model=%s bytes=%s sample_rate=%s duration_sec=%.3f rms=%.5f transcript_preview=%s",
            self._model_id,
            len(audio_bytes),
            sample_rate,
            duration_sec,
            rms,
            _safe_preview(transcript),
        )
        outputs = self._pipeline(audio_array, sampling_rate=sample_rate)
        scores: dict[EmotionLabel, float] = {label: 0.0 for label in EmotionLabel}
        for item in outputs:
            label = str(item.get("label", "")).lower()
            mapped = _LABEL_MAP.get(label)
            if mapped is None:
                continue
            scores[mapped] = max(scores[mapped], float(item.get("score", 0.0)))
        if sum(scores.values()) == 0.0:
            scores[EmotionLabel.NEUTRAL] = 1.0

        acoustic_summary = {
            "duration_sec": duration_sec,
            "rms": rms,
        }

        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_label, top_score = ordered[0]

        logger.info(
            "emotion_speech_response model=%s top=%s confidence=%.4f",
            self._model_id,
            top_label.value,
            top_score,
        )
        return SpeechEmotionBranchResult(
            raw_audio_reference=None,
            transcription=transcript,
            acoustic_scores=acoustic_summary,
            predicted_emotion=top_label,
            emotion_scores=scores,
            confidence=top_score,
            asr_metadata={},
            model_name=self._model_id,
            metadata={"adapter": "hf"},
        )


__all__ = ["HFSpeechEmotion"]
