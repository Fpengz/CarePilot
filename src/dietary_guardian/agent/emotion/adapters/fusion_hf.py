"""HF fusion adapter."""

from __future__ import annotations

from transformers import pipeline

from dietary_guardian.agent.emotion.ports import FusionPort
from dietary_guardian.features.companion.core.health.emotion import (
    EmotionContextFeatures,
    EmotionLabel,
    EmotionProductState,
)

_LABEL_MAP = {
    "happy": EmotionLabel.HAPPY,
    "joy": EmotionLabel.HAPPY,
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
    "confused": EmotionLabel.CONFUSED,
    "neutral": EmotionLabel.NEUTRAL,
}


def _product_state_for_label(label: EmotionLabel, *, trend: str) -> EmotionProductState:
    if label in {EmotionLabel.ANGRY, EmotionLabel.FRUSTRATED}:
        return EmotionProductState.DISTRESSED
    if label in {EmotionLabel.ANXIOUS, EmotionLabel.FEARFUL, EmotionLabel.SAD}:
        return EmotionProductState.NEEDS_REASSURANCE
    if label == EmotionLabel.CONFUSED:
        return EmotionProductState.CONFUSED
    if trend == "worsening" and label in {EmotionLabel.ANGRY, EmotionLabel.FRUSTRATED, EmotionLabel.SAD}:
        return EmotionProductState.DISTRESSED
    return EmotionProductState.STABLE


class HFFusion(FusionPort):
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

    def predict(
        self,
        *,
        text_scores: dict[EmotionLabel, float],
        speech_scores: dict[EmotionLabel, float] | None,
        context: EmotionContextFeatures,
    ) -> tuple[EmotionLabel, EmotionProductState, float, dict[EmotionLabel, float]]:
        speech_scores = speech_scores or {}
        features = {
            "text_scores": {k.value: v for k, v in text_scores.items()},
            "speech_scores": {k.value: v for k, v in speech_scores.items()},
            "context": {
                "recent_labels": [label.value for label in context.recent_labels],
                "trend": context.trend,
            },
        }
        prompt = f"Fusion features: {features}"
        self._ensure_pipeline()
        assert self._pipeline is not None
        outputs = self._pipeline(prompt)
        logits: dict[EmotionLabel, float] = {label: 0.0 for label in EmotionLabel}
        top_label = EmotionLabel.NEUTRAL
        top_score = 0.0
        for item in outputs[0]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).lower()
            mapped = _LABEL_MAP.get(label)
            if mapped is None:
                continue
            score = float(item.get("score", 0.0))
            logits[mapped] = max(logits[mapped], score)
            if score > top_score:
                top_label = mapped
                top_score = score
        if sum(logits.values()) == 0.0:
            logits[EmotionLabel.NEUTRAL] = 1.0
            top_label = EmotionLabel.NEUTRAL
            top_score = 1.0
        product_state = _product_state_for_label(top_label, trend=context.trend)
        return top_label, product_state, float(top_score), logits


__all__ = ["HFFusion"]
