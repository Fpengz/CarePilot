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
    "emotion": "anxious",
    "score": 0.76,
    "confidence_band": "high",
    "model_name": "ai_challenger_runtime",
    "model_version": "heuristic-v1",
    "evidence": [
      {"label": "anxious", "score": 0.76},
      {"label": "neutral", "score": 0.12}
    ],
    "transcription": null,
    "created_at": "2026-03-08T00:00:00Z",
    "request_id": "...",
    "correlation_id": "..."
  }
}
```
