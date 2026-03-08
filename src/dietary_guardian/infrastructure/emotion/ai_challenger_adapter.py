from __future__ import annotations

from dietary_guardian.models.emotion import EmotionInferenceResult

# Pinned upstream provenance for selective extraction compatibility.
AI_CHALLENGER_SOURCE_COMMIT = "9afc3f1a3a3fec71a4e5920d8f4103710b337ecc"


def to_compat_response(result: EmotionInferenceResult) -> dict[str, object]:
    return {
        "emotion": result.emotion.value,
        "confidence": float(result.score),
        "emotions": {item.label.value: float(item.score) for item in result.evidence},
        "source_type": result.source_type,
        "transcription": result.transcription,
        "model_name": result.model_name,
        "model_version": result.model_version,
    }

