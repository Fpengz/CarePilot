Chat recent activity context.

Summary:
- Included recent workflow timeline events in chat context formatting.
- Passed per-user timeline events into chat prompt assembly.

Tests:
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/api/test_chat_context.py`
