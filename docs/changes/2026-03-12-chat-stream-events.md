Chat stream event refactor.

Summary:
- Added `ChatAgent.stream_events` to yield typed `ChatStreamEvent` envelopes.
- Kept `ChatAgent.stream` as the SSE string wrapper around structured events.

Tests:
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/agent/test_chat_stream_events.py`
