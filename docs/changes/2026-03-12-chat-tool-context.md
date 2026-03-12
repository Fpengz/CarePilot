Chat tool context exposure.

Summary:
- Added optional tool summaries to the chat context formatter.
- Injected registered tool specs into chat prompts to surface available actions.

Tests:
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/api/test_chat_context.py`
