# Emotion Integration (Phase 1)

This branch integrates `linm0034/ai_challenger` capability into Dietary Guardian as an in-process runtime behind application ports.

## Upstream provenance

- Source repository: `https://github.com/linm0034/ai_challenger`
- Pinned source commit: `9afc3f1a3a3fec71a4e5920d8f4103710b337ecc`
- Integration mode: selective extraction into the in-process runtime used by the API layer

## New runtime flags

- `EMOTION_INFERENCE_ENABLED` (default: `false`)
- `EMOTION_SPEECH_ENABLED` (default: `false`)
- `EMOTION_REQUEST_TIMEOUT_SECONDS` (default: `15.0`)
- `EMOTION_MODEL_DEVICE` (default: `auto`)
- `EMOTION_TEXT_MODEL_ID`
- `EMOTION_SPEECH_MODEL_ID`
- `EMOTION_SOURCE_COMMIT`

## Contract approach

- Canonical routes: `/api/v1/emotions/*`
- Routes are policy-protected for inference, health is public.
