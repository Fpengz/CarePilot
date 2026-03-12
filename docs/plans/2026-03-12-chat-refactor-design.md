# Chat Refactor Design (2026-03-12)

## Summary
Refactor `agent/chat` into a canonical bounded agent with typed schemas,
runtime-driven inference, and structured SSE events. All behavior changes
must be written to a local markdown change log for review.

## Key Decisions
- Chat now emits `data: {"event": ..., "data": {...}}` SSE envelopes.
- Classification, summarization, code generation, and metric extraction use
  the shared `InferenceEngine` with SEA-LION runtime wiring.
- Streaming is handled by a dedicated chat runtime adapter that owns the
  AsyncOpenAI client and retry/backoff policy.
- Chat routes keep their existing responsibilities but use typed outputs and
  structured logging.

## Risks
- SSE payload format changes require frontend updates.
- SEA-LION streaming behavior differences may affect token cadence; retries
  may slightly delay error signaling.

## Validation
- Manual API exercise: `/api/v1/chat` returns structured SSE events.
- Ensure chat history and dashboard endpoints still load without runtime errors.
