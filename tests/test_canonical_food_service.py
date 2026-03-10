"""Tests for canonical food service."""

from __future__ import annotations

from dietary_guardian.domain.recommendations.models import CanonicalFoodRecord
from dietary_guardian.models.meal import Nutrition
from dietary_guardian.domain.recommendations.canonical_food_matching import (
    build_default_canonical_food_records,
    find_food_by_name,
    rank_food_candidates,
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


def test_rank_food_candidates_prefers_component_and_preparation_fit() -> None:
    char_kway_teow = CanonicalFoodRecord(
        food_id="ckt",
        title="Char Kway Teow",
        aliases=["Char Kway Teow"],
        aliases_normalized=["char kway teow"],
        slot="lunch",
        venue_type="hawker",
        cuisine_tags=["local"],
        ingredient_tags=["kway teow", "egg", "cockles", "lard"],
        preparation_tags=["fried", "noodles"],
        nutrition=Nutrition(calories=700, carbs_g=80, sugar_g=8, protein_g=20, fat_g=30, sodium_mg=1200),
    )
    kway_teow_soup = CanonicalFoodRecord(
        food_id="soup",
        title="Kway Teow Soup",
        aliases=["Kway Teow Soup"],
        aliases_normalized=["kway teow soup"],
        slot="lunch",
        venue_type="hawker",
        cuisine_tags=["local"],
        ingredient_tags=["kway teow", "fish cake", "soup"],
        preparation_tags=["soup", "noodles"],
        nutrition=Nutrition(calories=400, carbs_g=55, sugar_g=4, protein_g=15, fat_g=8, sodium_mg=700),
    )

    ranked = rank_food_candidates(
        records=[char_kway_teow, kway_teow_soup],
        locale="en-SG",
        observed_label="kway teow",
        candidate_aliases=["char kway teow"],
        detected_components=["egg", "cockles"],
        preparation="fried",
    )

    assert ranked
    assert ranked[0][0].food_id == "ckt"
    assert ranked[0][1] > ranked[1][1]
