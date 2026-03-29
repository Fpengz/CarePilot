"""Ensure default canonical food loader includes hawker and canonical seeds."""

from __future__ import annotations

from care_pilot.platform.persistence.food.ingestion import load_default_canonical_food_records


def test_default_loader_includes_hawker_and_canonical() -> None:
    records = load_default_canonical_food_records()
    titles = {item.title for item in records}
    food_ids = {item.food_id for item in records}

    assert "Laksa" in titles
    assert "local.hainanese_chicken_rice" in food_ids
