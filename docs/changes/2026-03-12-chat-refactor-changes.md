# Chat Refactor Change Log (2026-03-12)

This file records behavior and contract changes introduced by the chat refactor.

## Behavior Changes
- Chat SSE payloads now use an event envelope: `{"event": "...", "data": {...}}`.
- This SSE format is not backward compatible with the previous `{text}`/`{done}` payloads.
- Streaming errors emit explicit `event="error"` payloads with structured details.
- Chat streaming uses retry/backoff when the SEA-LION stream fails to start.
- Router classification uses typed output parsing with a strict fallback to `general`.
- Code-route LLM requests no longer use `thinking_mode=on`; code is generated using the standard chat model prompt.

## Contract Changes
- `ChatAgent` now implements `BaseAgent` and exposes a typed `run()` entrypoint.
- Chat modules depend on a shared runtime adapter instead of direct OpenAI clients.
- New chat stream settings: `CHAT_STREAM_MAX_RETRIES`, `CHAT_STREAM_BACKOFF_SECONDS`.
