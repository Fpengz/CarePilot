"""HF text emotion adapter."""

from __future__ import annotations

import re

from care_pilot.agent.emotion.schemas import EmotionLabel, TextEmotionBranchResult
from care_pilot.config.app import get_settings
from care_pilot.features.companion.emotion.ports import TextEmotionPort
from care_pilot.platform.observability import get_logger
from care_pilot.platform.observability.payloads import pretty_json_payload
from care_pilot.platform.runtime.hf_loader import get_hf_loader

logger = get_logger(__name__)

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


def _safe_preview(text: str, *, limit: int = 160) -> str:
    preview = text[:limit].replace("\n", " ")
    preview = re.sub(r"[0-9]", "x", preview)
    preview = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[redacted-email]", preview)
    return preview


class HFTextEmotion(TextEmotionPort):
    def __init__(self, model_id: str, device: str, cache_dir: str | None = None) -> None:
        self._model_id = model_id
        self._device = 0 if device == "cuda" else -1
        self._cache_dir = cache_dir
        self._pipeline = None

    def _ensure_pipeline(self) -> None:
        if self._pipeline is not None:
            return
        self._pipeline = get_hf_loader(
            self._model_id,
            task="text-classification",
            cache_dir=self._cache_dir,
            return_all_scores=True,
            device=self._device,
        )

    def predict(self, text: str, language: str | None) -> TextEmotionBranchResult:
        del language
        self._ensure_pipeline()
        assert self._pipeline is not None
        settings = get_settings()
        if settings.observability.log_hf_payloads:
            outbound_payload = {
                "model_id": self._model_id,
                "text": text,
                "text_len": len(text),
            }
            logger.info("hf_api_outbound payload=%s", pretty_json_payload(outbound_payload))
        logger.info(
            "emotion_text_request model=%s text_len=%s preview=%s",
            self._model_id,
            len(text),
            _safe_preview(text),
        )
        outputs = self._pipeline(text)
        scores: dict[EmotionLabel, float] = dict.fromkeys(EmotionLabel, 0.0)
        if isinstance(outputs, list) and outputs:
            if isinstance(outputs[0], dict):
                items = outputs
            elif isinstance(outputs[0], list):
                items = outputs[0]
            else:
                items = []
        else:
            items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).lower()
            mapped = _LABEL_MAP.get(label)
            if mapped is None:
                continue
            scores[mapped] = max(scores[mapped], float(item.get("score", 0.0)))
        if sum(scores.values()) == 0.0:
            scores[EmotionLabel.NEUTRAL] = 1.0

        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_label, top_score = ordered[0]

        logger.info(
            "emotion_text_response model=%s top=%s confidence=%.4f",
            self._model_id,
            top_label.value,
            top_score,
        )
        result = TextEmotionBranchResult(
            transcript_or_text=text,
            emotion_scores=scores,
            predicted_emotion=top_label,
            confidence=top_score,
            model_name=self._model_id,
            metadata={"adapter": "hf"},
        )
        if settings.observability.log_hf_payloads:
            inbound_payload = {
                "model_id": self._model_id,
                "output": result.model_dump(mode="json"),
            }
            logger.info("hf_api_inbound payload=%s", pretty_json_payload(inbound_payload))
        return result


__all__ = ["HFTextEmotion"]
