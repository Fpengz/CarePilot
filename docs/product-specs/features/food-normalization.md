# Food Normalization Dataset

This document defines the canonical food dataset format used to normalize
meal perception results. The dataset is stored under:

```
src/care_pilot/data/food/
```

The system merges:
- `canonical_foods.json` (curated canonical records)
- `sg_hawker_food.json` (local hawker seed data)
- optional imports from USDA/Open Food Facts

## Canonical food record format

Each entry in `canonical_foods.json` must conform to
`CanonicalFoodRecord` (see `features/recommendations/domain/models.py`).
Required fields:

```json
{
  "food_id": "local.hainanese_chicken_rice",
  "title": "Hainanese Chicken Rice",
  "locale": "en-SG",
  "aliases": ["Chicken Rice"],
  "aliases_normalized": ["hainanese chicken rice", "chicken rice"],
  "slot": "lunch",
  "venue_type": "hawker",
  "cuisine_tags": ["singapore"],
  "ingredient_tags": ["chicken", "rice", "ginger"],
  "preparation_tags": ["steamed"],
  "nutrition": {
    "calories": 520,
    "carbs_g": 60,
    "sugar_g": 2,
    "protein_g": 32,
    "fat_g": 12,
    "sodium_mg": 720,
    "fiber_g": 1
  },
  "price_tier": "budget",
  "health_tags": ["protein_rich"],
  "risk_tags": ["high_sodium"],
  "glycemic_index_label": "medium",
  "glycemic_index_value": 55,
  "disease_advice": {},
  "alternatives": [],
  "serving_size": "1 plate",
  "default_portion_grams": 320,
  "portion_references": [{"unit": "plate", "grams": 320, "confidence": 0.7}],
  "source_dataset": "local_seed",
  "source_type": "seed",
  "active": true
}
```

## Hawker seed format

`sg_hawker_food.json` entries include localized names, nutrition, health
tags, and disease-specific advice. These records are merged into the
canonical food index at runtime and during ingestion.

Required keys:
- `food_id`
- `food_name_en`
- `category`
- `cuisine`
- `source`
- `serving_size`
- `nutrition_per_serving`

Optional keys:
- `glycemic_index`, `gi_value`
- `health_tags`
- `disease_advice`
- `healthier_alternatives`

## Ingestion

To seed SQLite with the full canonical food set (canonical + hawker + imports):

```
uv run python scripts/cli.py ingest canonical --reset
```

To load the hawker/drink vector index for retrieval:

```
uv run python scripts/cli.py ingest local
```
