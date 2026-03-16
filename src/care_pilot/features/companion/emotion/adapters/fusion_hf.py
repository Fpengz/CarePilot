"""HF fusion adapter."""

from __future__ import annotations

import re
from transformers import pipeline

from care_pilot.config.app import get_settings
from care_pilot.features.companion.emotion.ports import FusionPort
from care_pilot.agent.emotion.schemas import (
    EmotionContextFeatures,
    EmotionLabel,
    EmotionProductState,
    TextEmotionBranchResult,
    SpeechEmotionBranchResult,
    EmotionFusionOutput,
    FusionTrace,
)
from care_pilot.platform.observability import get_logger
from care_pilot.platform.observability.payloads import pretty_json_payload

logger = get_logger(__name__)

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


def _safe_preview(text: str, *, limit: int = 160) -> str:
    preview = text[:limit].replace("\n", " ")
    preview = re.sub(r"[0-9]", "x", preview)
    preview = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[redacted-email]", preview)
    return preview


def _product_state_for_label(label: EmotionLabel, *, trend: str) -> EmotionProductState:
    if label in {EmotionLabel.ANGRY, EmotionLabel.FRUSTRATED}:
        return EmotionProductState.DISTRESSED
    if label in {EmotionLabel.ANXIOUS, EmotionLabel.FEARFUL, EmotionLabel.SAD}:
        return EmotionProductState.NEEDS_REASSURANCE
    if label == EmotionLabel.CONFUSED:
        return EmotionProductState.CONFUSED
    if trend == "worsening" and label in {
        EmotionLabel.ANGRY,
        EmotionLabel.FRUSTRATED,
        EmotionLabel.SAD,
    }:
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
        text_branch: TextEmotionBranchResult | None,
        speech_branch: SpeechEmotionBranchResult | None,
        context: EmotionContextFeatures,
    ) -> tuple[EmotionFusionOutput, FusionTrace]:
        settings = get_settings()
        text_scores = text_branch.emotion_scores if text_branch else {}
        speech_scores = speech_branch.emotion_scores if speech_branch else {}
        features = {
            "text_scores": {k.value: v for k, v in text_scores.items()},
            "speech_scores": {k.value: v for k, v in speech_scores.items()},
            "context": {
                "recent_labels": [label.value for label in context.recent_labels],
                "trend": context.trend,
            },
        }
        if settings.observability.log_hf_payloads:
            outbound_payload = {
                "model_id": self._model_id,
                "features": features,
            }
            logger.info("hf_api_outbound payload=%s", pretty_json_payload(outbound_payload))
        prompt = f"Fusion features: {features}"
        self._ensure_pipeline()
        assert self._pipeline is not None
        logger.info(
            "emotion_fusion_request model=%s prompt_preview=%s",
            self._model_id,
            _safe_preview(prompt),
        )
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

        logger.info(
            "emotion_fusion_response model=%s top=%s confidence=%.4f product_state=%s",
            self._model_id,
            top_label.value,
            top_score,
            product_state.value,
        )
        output = EmotionFusionOutput(
            emotion_label=top_label,
            product_state=product_state,
            confidence=float(top_score),
            logits=logits,
        )
        trace = FusionTrace(
            fusion_inputs=features,
            weighting_strategy="hf-text-classification-head",
            conflict_resolution="argmax",
            final_decision_reason=f"Top fused score was {top_score:.2f} for {top_label.value}",
        )
        if settings.observability.log_hf_payloads:
            inbound_payload = {
                "model_id": self._model_id,
                "output": output.model_dump(mode="json"),
                "trace": trace.model_dump(mode="json"),
            }
            logger.info("hf_api_inbound payload=%s", pretty_json_payload(inbound_payload))
        return output, trace


__all__ = ["HFFusion"]
