# API Contract: Emotions (Phase 1)

## Runtime notes
- Routes live under `/api/v1/emotions/*`.
- Text and speech inference are feature-flagged.
- The in-process runtime is extracted from the teammate `ai_challenger` integration and kept behind application and infrastructure boundaries.
- Relevant runtime flags:
  - `EMOTION_INFERENCE_ENABLED`
  - `EMOTION_SPEECH_ENABLED`
  - `EMOTION_REQUEST_TIMEOUT_SECONDS`
  - `EMOTION_MODEL_DEVICE`
  - `EMOTION_TEXT_MODEL_ID`
  - `EMOTION_SPEECH_MODEL_ID`
  - `EMOTION_SOURCE_COMMIT`

## DG-native routes

- `GET /api/v1/emotions/health`
- `POST /api/v1/emotions/text`
- `POST /api/v1/emotions/speech`

## Request examples

### `POST /api/v1/emotions/text`

```json
{
  "text": "I feel anxious and overwhelmed.",
  "language": "en"
}
```

## Response example

```json
{
  "observation": {
    "source_type": "text",
    "text_branch": {
      "transcript": "I feel anxious and overwhelmed.",
      "model_name": "j-hartmann/emotion-english-distilroberta-base",
      "model_version": "hf",
      "scores": {"anxious": 0.76, "neutral": 0.12}
    },
    "speech_branch": null,
    "context_features": {
      "recent_labels": ["neutral", "anxious"],
      "trend": "worsening"
    },
    "fusion": {
      "emotion_label": "anxious",
      "product_state": "needs_reassurance",
      "confidence": 0.72,
      "logits": {"anxious": 0.72, "neutral": 0.18}
    },
    "created_at": "2026-03-08T00:00:00Z",
    "request_id": "...",
    "correlation_id": "..."
  }
}
```
