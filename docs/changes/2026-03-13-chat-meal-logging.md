# Chat meal logging + personalization

## Summary
- Add heuristic + LLM fallback meal logging intent detection.
- Propose meal logging with inline confirmation in chat UI.
- Add confirm endpoint to log meals after user approval.
- Expand chat prompt context with full health profile details.

## Files touched
- `apps/api/dietary_api/routers/chat.py`
- `apps/api/dietary_api/services/chat_meal_intent.py`
- `apps/web/app/chat/page.tsx`
- `src/dietary_guardian/features/companion/core/chat_context.py`
- `tests/api/test_chat_meal_intent.py`
- `tests/api/test_chat_meal_confirm.py`
- `tests/api/test_chat_context.py`

## Validation
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/api/test_chat_meal_intent.py`
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/api/test_chat_meal_confirm.py`
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/api/test_chat_context.py -k health_profile`
