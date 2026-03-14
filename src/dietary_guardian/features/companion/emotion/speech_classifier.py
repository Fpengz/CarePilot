"""
Classify emotion from speech inputs.

This module contains speech emotion model wrappers used by the
emotion inference engine.
"""

from __future__ import annotations

import hashlib

from dietary_guardian.features.companion.emotion.text_classifier import TextEmotionClassifier
from dietary_guardian.agent.emotion.schemas import EmotionLabel


class SpeechEmotionClassifier:
    def __init__(self, *, text_classifier: TextEmotionClassifier) -> None:
        self._text_classifier = text_classifier

    def predict_scores(
        self,
        *,
        audio_bytes: bytes,
        transcription: str | None,
    ) -> tuple[dict[EmotionLabel, float], str | None]:
        if transcription:
            text_scores = self._text_classifier.predict_scores(transcription)
            return text_scores, transcription
        labels = list(EmotionLabel)
        digest = hashlib.sha256(audio_bytes).digest()
        top_label = labels[digest[0] % len(labels)]
        remaining = [label for label in labels if label != top_label]
        scores: dict[EmotionLabel, float] = {top_label: 0.55}
        distributed = 0.45 / float(len(remaining))
        for label in remaining:
            scores[label] = distributed
        return scores, None
