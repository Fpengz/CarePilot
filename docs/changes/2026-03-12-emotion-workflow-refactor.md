# Emotion workflow refactor

## Summary
- Add explicit `disabled` health status when emotion inference is turned off.
- Avoid invoking emotion inference in chat when the feature or speech mode is disabled.
- Move session-scoped emotion helpers into the API layer to keep feature code free of HTTP wiring.

## Files touched
- `src/care_pilot/features/companion/core/health/emotion.py`
- `src/care_pilot/agent/emotion/agent.py`
- `apps/api/carepilot_api/routers/chat.py`
- `apps/api/carepilot_api/routers/emotions.py`
- `apps/api/carepilot_api/services/emotion_session.py`

## Validation
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/api/test_api_emotions.py -k "health_returns_disabled"`
