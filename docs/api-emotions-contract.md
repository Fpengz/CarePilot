# API Contract: Emotions (Phase 1)

## DG-native routes

- `GET /api/v1/emotions/health`
- `POST /api/v1/emotions/text`
- `POST /api/v1/emotions/speech`

## Compatibility routes

- `GET /emotion/health`
- `POST /emotion/text`
- `POST /emotion/speech`

## Request examples

### `POST /api/v1/emotions/text`

```json
{
  "text": "I feel anxious and overwhelmed.",
  "language": "en"
}
```

### `POST /emotion/text`

```json
{
  "text": "I feel anxious and overwhelmed."
}
```

## Response examples

### Native response

```json
{
  "observation": {
    "source_type": "text",
    "emotion": "anxious",
    "score": 0.76,
    "confidence_band": "high",
    "model_name": "ai_challenger_compatible_runtime",
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

### Compatibility response

```json
{
  "emotion": "anxious",
  "confidence": 0.76,
  "emotions": {
    "anxious": 0.76,
    "neutral": 0.12
  },
  "source_type": "text",
  "transcription": null,
  "model_name": "ai_challenger_compatible_runtime",
  "model_version": "heuristic-v1"
}
```
