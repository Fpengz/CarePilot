from __future__ import annotations

from dietary_guardian.models.emotion import EmotionLabel

_KEYWORDS: dict[EmotionLabel, tuple[str, ...]] = {
    EmotionLabel.HAPPY: ("happy", "glad", "great", "good", "relieved", "calm", "joy"),
    EmotionLabel.SAD: ("sad", "down", "unhappy", "depressed", "upset"),
    EmotionLabel.ANGRY: ("angry", "mad", "furious", "rage"),
    EmotionLabel.FRUSTRATED: ("frustrated", "annoyed", "irritated", "stuck"),
    EmotionLabel.ANXIOUS: ("anxious", "worried", "panic", "nervous", "stress"),
    EmotionLabel.NEUTRAL: ("okay", "fine", "normal", "neutral"),
    EmotionLabel.CONFUSED: ("confused", "unsure", "unclear", "lost"),
    EmotionLabel.FEARFUL: ("afraid", "fear", "scared", "terrified"),
}


class TextEmotionClassifier:
    def predict_scores(self, text: str) -> dict[EmotionLabel, float]:
        lowered = text.lower()
        base_scores = {label: 0.05 for label in EmotionLabel}
        base_scores[EmotionLabel.NEUTRAL] = 0.30
        for label, words in _KEYWORDS.items():
            for word in words:
                if word in lowered:
                    base_scores[label] += 0.20
        total = sum(base_scores.values())
        if total <= 0:
            return {EmotionLabel.NEUTRAL: 1.0}
        return {label: score / total for label, score in base_scores.items()}

