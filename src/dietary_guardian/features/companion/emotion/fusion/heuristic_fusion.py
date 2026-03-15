"""
Heuristic-based emotion fusion.
"""

from __future__ import annotations

from dietary_guardian.features.companion.emotion.ports import FusionPort
from dietary_guardian.agent.emotion.schemas import (
    EmotionContextFeatures,
    EmotionLabel,
    EmotionProductState,
    TextEmotionBranchResult,
    SpeechEmotionBranchResult,
    EmotionFusionOutput,
    FusionTrace,
)

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

class HeuristicFusion(FusionPort):
    def __init__(self, text_weight: float = 0.6, speech_weight: float = 0.4) -> None:
        self._text_weight = text_weight
        self._speech_weight = speech_weight

    def predict(
        self,
        *,
        text_branch: TextEmotionBranchResult | None,
        speech_branch: SpeechEmotionBranchResult | None,
        context: EmotionContextFeatures,
    ) -> tuple[EmotionFusionOutput, FusionTrace]:
        text_scores = text_branch.emotion_scores if text_branch else {label: 0.0 for label in EmotionLabel}
        speech_scores = speech_branch.emotion_scores if speech_branch else {label: 0.0 for label in EmotionLabel}
        
        # Weighted average of logits/probabilities
        fused_logits: dict[EmotionLabel, float] = {}
        for label in EmotionLabel:
            t = text_scores.get(label, 0.0)
            s = speech_scores.get(label, 0.0)
            
            if text_branch and speech_branch:
                fused_logits[label] = (t * self._text_weight) + (s * self._speech_weight)
            elif text_branch:
                fused_logits[label] = t
            elif speech_branch:
                fused_logits[label] = s
            else:
                fused_logits[label] = 0.0
                
        if sum(fused_logits.values()) == 0.0:
            fused_logits[EmotionLabel.NEUTRAL] = 1.0
            
        ordered = sorted(fused_logits.items(), key=lambda item: item[1], reverse=True)
        top_label, top_score = ordered[0]
        
        product_state = _product_state_for_label(top_label, trend=context.trend)
        
        output = EmotionFusionOutput(
            emotion_label=top_label,
            product_state=product_state,
            confidence=top_score,
            logits=fused_logits,
        )
        trace = FusionTrace(
            fusion_inputs={
                "text_scores": {k.value: v for k, v in text_scores.items()},
                "speech_scores": {k.value: v for k, v in speech_scores.items()},
            },
            weighting_strategy=f"heuristic-weighted (text:{self._text_weight}, speech:{self._speech_weight})",
            final_decision_reason=f"Weighted sum gave {top_score:.2f} for {top_label.value}",
        )
        return output, trace
