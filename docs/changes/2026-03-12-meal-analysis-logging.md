Meal analysis logging updates.

Summary:
- Added structured payload helpers for meal analysis logging.
- Added model resolution for meal analysis log metadata.
- Emitted a standardized `meal_analysis_completed` log event after analysis.

Tests:
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/features/test_meal_analysis_logging.py`
