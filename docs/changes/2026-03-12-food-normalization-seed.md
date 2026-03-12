# Food normalization seed and ingestion

## Summary
- Add a canonical food seed dataset (`canonical_foods.json`) alongside existing SG food data.
- Load canonical seed records into the default canonical food registry for meal normalization.
- Expose a new CLI command to ingest canonical foods into SQLite.

## Commands
```
uv run python scripts/cli.py ingest canonical --reset
```

## Files touched
- `src/dietary_guardian/data/food/canonical_foods.json`
- `src/dietary_guardian/platform/persistence/food/ingestion.py`
- `src/dietary_guardian/platform/persistence/food/__init__.py`
- `src/dietary_guardian/features/recommendations/domain/canonical_food_matching.py`
- `scripts/cli.py`
- `tests/platform/test_food_ingestion.py`
- `tests/domain/test_canonical_food_service.py`

## Validation
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/platform/test_food_ingestion.py`
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/domain/test_canonical_food_service.py -k "canonical_seed"`
