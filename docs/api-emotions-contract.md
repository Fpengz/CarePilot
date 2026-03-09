# API Contract: Emotions (Phase 1)

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
