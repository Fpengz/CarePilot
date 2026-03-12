"""HF speech emotion adapter."""

from __future__ import annotations

import io

import numpy as np
import soundfile as sf
from transformers import pipeline

from dietary_guardian.agent.emotion.ports import SpeechEmotionPort
from dietary_guardian.features.companion.core.health.emotion import EmotionLabel

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
    ) -> tuple[dict[EmotionLabel, float], dict[str, float], str, str]:
        del transcript
        data, sample_rate = sf.read(io.BytesIO(audio_bytes))
        if isinstance(data, np.ndarray) and data.ndim > 1:
            data = np.mean(data, axis=1)
        audio_array = data.astype(np.float32)
        duration_sec = float(len(audio_array) / sample_rate) if sample_rate else 0.0
        rms = float(np.sqrt(np.mean(np.square(audio_array)))) if len(audio_array) else 0.0

        self._ensure_pipeline()
        assert self._pipeline is not None
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
        return scores, acoustic_summary, self._model_id, "hf"


__all__ = ["HFSpeechEmotion"]
