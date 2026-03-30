"""Tests for food ingestion helpers."""

from __future__ import annotations

import json

from care_pilot.features.meals.domain.models import Nutrition
from care_pilot.features.recommendations.domain.models import CanonicalFoodRecord
from care_pilot.platform.persistence.food.ingestion import load_canonical_food_records


def test_load_canonical_food_records_from_json(tmp_path) -> None:
    record = CanonicalFoodRecord(
        food_id="local.hainanese_chicken_rice",
        title="Hainanese Chicken Rice",
        aliases=["Chicken Rice"],
        aliases_normalized=["hainanese chicken rice", "chicken rice"],
        slot="lunch",
        venue_type="hawker",
        cuisine_tags=["singapore"],
        preparation_tags=["steamed"],
        nutrition=Nutrition(
            calories=520,
            carbs_g=60,
            sugar_g=2,
            protein_g=32,
            fat_g=12,
            sodium_mg=720,
        ),
        source_dataset="local_seed",
        source_type="seed",
    )
    path = tmp_path / "canonical_foods.json"
    path.write_text(json.dumps([record.model_dump(mode="json")]))

    records = load_canonical_food_records(path)

    assert len(records) == 1
    assert records[0].food_id == record.food_id
