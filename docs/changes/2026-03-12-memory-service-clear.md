Memory service consistency pass.

Summary:
- Added `clear` semantics and basic locking to profile and clinical snapshot memory services.
- Added tests for per-user clearing of memory caches.

Tests:
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/application/test_memory_services.py`
