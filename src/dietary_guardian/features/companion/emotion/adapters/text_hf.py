"""HF text emotion adapter."""

from __future__ import annotations

from transformers import pipeline

from dietary_guardian.features.companion.emotion.ports import TextEmotionPort
from dietary_guardian.agent.emotion.schemas import EmotionLabel

_LABEL_MAP = {
    "joy": EmotionLabel.HAPPY,
    "happiness": EmotionLabel.HAPPY,
    "happy": EmotionLabel.HAPPY,
    "sad": EmotionLabel.SAD,
    "sadness": EmotionLabel.SAD,
    "anger": EmotionLabel.ANGRY,
    "angry": EmotionLabel.ANGRY,
    "frustration": EmotionLabel.FRUSTRATED,
    "frustrated": EmotionLabel.FRUSTRATED,
    "anxiety": EmotionLabel.ANXIOUS,
    "anxious": EmotionLabel.ANXIOUS,
    "fear": EmotionLabel.FEARFUL,
    "fearful": EmotionLabel.FEARFUL,
    "confusion": EmotionLabel.CONFUSED,
    "confused": EmotionLabel.CONFUSED,
    "neutral": EmotionLabel.NEUTRAL,
}


class HFTextEmotion(TextEmotionPort):
    def __init__(self, model_id: str, device: str) -> None:
        self._model_id = model_id
        self._device = 0 if device == "cuda" else -1
        self._pipeline = None

    def _ensure_pipeline(self) -> None:
        if self._pipeline is not None:
            return
        self._pipeline = pipeline(
            "text-classification",
            model=self._model_id,
            return_all_scores=True,
            device=self._device,
        )

    def predict(self, text: str, language: str | None) -> tuple[dict[EmotionLabel, float], str, str]:
        del language
        self._ensure_pipeline()
        assert self._pipeline is not None
        outputs = self._pipeline(text)
        scores: dict[EmotionLabel, float] = {label: 0.0 for label in EmotionLabel}
        for item in outputs[0]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).lower()
            mapped = _LABEL_MAP.get(label)
            if mapped is None:
                continue
            scores[mapped] = max(scores[mapped], float(item.get("score", 0.0)))
        if sum(scores.values()) == 0.0:
            scores[EmotionLabel.NEUTRAL] = 1.0
        return scores, self._model_id, "hf"


__all__ = ["HFTextEmotion"]
