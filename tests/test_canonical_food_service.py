from __future__ import annotations

from dietary_guardian.services.canonical_food_service import (
    build_default_canonical_food_records,
    find_food_by_name,
)


def test_default_canonical_food_records_include_teammate_hawker_seed() -> None:
    records = build_default_canonical_food_records()

    laksa = next((item for item in records if item.title == "Laksa"), None)

    assert laksa is not None
    assert laksa.glycemic_index_label == "medium"
    assert laksa.glycemic_index_value == 55
    assert "very_high_sodium" in laksa.health_tags
    assert "high_sodium" in laksa.risk_tags
    assert laksa.default_portion_grams is not None
    assert laksa.portion_references
    assert laksa.disease_advice["hypertension"].risk_level == "high"
    assert laksa.alternatives


def test_find_food_by_name_matches_aliases_and_variants() -> None:
    records = build_default_canonical_food_records()

    match = find_food_by_name(records, "Mee-Siam (with gravy)", locale="en-SG")

    assert match is not None
    assert match.title == "Mee Siam"
    assert "mee siam" in match.aliases_normalized
