# Emotion Pipeline Refactor Design

## Goal
Refactor emotion inference to match `emotion-workflow.md` with an injectable multimodal pipeline and a full-trace API response, defaulting to MERaLiON ASR and HF model adapters (text, speech, fusion).

## Architecture Overview
- Introduce an orchestration pipeline with injectable ports for ASR, text emotion, speech emotion, and fusion.
- Keep feature logic decoupled from HTTP by routing session-specific behavior through API services.
- Maintain a full trace response that exposes branch outputs, context features, and fusion output.

## Data Flow
1. **Input**
   - `/api/v1/emotions/text`: `{text, language}`
   - `/api/v1/emotions/speech`: audio bytes + optional `transcription`, `language`
2. **ASR**
   - Speech requests run ASR (default MERaLiON, configurable) to produce a transcript.
   - Provided transcription is retained but ASR still runs for alignment.
3. **Text Branch**
   - Process transcript/input text with text model to output label scores + metadata.
4. **Speech Branch**
   - Process audio to output label scores + acoustic summary + metadata.
5. **Context Features**
   - Pull last N (configurable, default 5) emotion observations from the timeline.
   - Derive trend signals (worsening/stable/improving) and recent distribution features.
6. **Fusion**
   - Fusion model consumes structured inputs and outputs final `emotion_label`, `product_state`, confidence/logits.
7. **Output**
   - Full trace response containing text branch, speech branch, context features, and fusion output.

## Error Handling
- `503` with `emotions.not_configured` when model backends are missing.
- `422` with `emotions.asr_failed` when ASR fails.
- `504` with `emotions.timeout` for timeouts.
- `400` with `emotions.invalid_input` for invalid payloads.
- Health endpoint returns `disabled` if inference is off and `degraded` if caches are cold.

## Defaults & Config
- ASR: MERaLiON (configurable).
- Text model: `j-hartmann/emotion-english-distilroberta-base`.
- Speech model: `meralion/speech-emotion-recognition`.
- Fusion model: `dynann/multimodal-emotion-speech-recognition`.
- History window: configurable (default 5).

## API Contract
- Breaking change to `/api/v1/emotions/*` response shape with new full-trace schema.
- Update `docs/references/api/emotions.md` with the new response example and fields.

## Testing
- Update capability tests to use stub ports and validate trace shape, fusion output, and context features.
- Update API tests to assert new fields and error mapping.
- Add unit test for history window behavior.
