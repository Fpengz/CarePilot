"""Canonical food matching and ranking logic.

Builds ``CanonicalFoodRecord`` objects from seed data sources (default meal
catalog, USDA, Open Food Facts, and the local SG hawker seed) and provides
fuzzy name-based ranking so vision-agent labels can be resolved to canonical
records.

``normalize_text``, ``rank_food_candidates``, and ``find_food_by_name`` are
the main public surfaces used by meal analysis use cases.
``build_default_canonical_food_records`` bootstraps the full record set once
at startup.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from dietary_guardian.domain.identity.models import MealSlot
from dietary_guardian.domain.meals import PortionReference
from dietary_guardian.domain.recommendations.meal_catalog_queries import DEFAULT_MEAL_CATALOG
from dietary_guardian.domain.recommendations.models import (
    CanonicalFoodAdvice,
    CanonicalFoodAlternative,
    CanonicalFoodRecord,
    MealCatalogItem,
)
from dietary_guardian.domain.meals.models import Nutrition


def normalize_text(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return " ".join(cleaned.split())


def _package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _teammate_seed_path() -> Path:
    return _package_root() / "data" / "food" / "sg_hawker_food.json"


def _usda_seed_path() -> Path:
    return _package_root() / "data" / "food" / "usda_foods.json"


def _open_food_facts_seed_path() -> Path:
    return _package_root() / "data" / "food" / "open_food_facts_products.json"


def _slot_from_category(category: str) -> MealSlot:
    normalized = normalize_text(category)
    if "breakfast" in normalized:
        return "breakfast"
    if "bread" in normalized or "pastry" in normalized:
        return "breakfast"
    if "drink" in normalized or "dessert" in normalized or "snack" in normalized:
        return "snack"
    if "dinner" in normalized:
        return "dinner"
    return "lunch"


def _price_tier(source: str, calories: float) -> str:
    source_normalized = normalize_text(source)
    if "hawker" in source_normalized or "kopitiam" in source_normalized:
        return "budget"
    if calories >= 650:
        return "moderate"
    return "budget"


def _preparation_tags(name: str, source: str) -> list[str]:
    searchable = normalize_text(f"{name} {source}")
    tags: list[str] = []
    for token, label in (
        ("soup", "soup"),
        ("rice", "rice"),
        ("noodle", "noodles"),
        ("mee", "noodles"),
        ("fried", "fried"),
        ("toast", "toast"),
        ("steamed", "steamed"),
        ("grilled", "grilled"),
        ("roti", "flatbread"),
    ):
        if token in searchable and label not in tags:
            tags.append(label)
    return tags


def _aliases(entry: dict[str, object]) -> list[str]:
    values = [
        str(entry.get("food_name_en") or "").strip(),
        str(entry.get("food_name_cn") or "").strip(),
        str(entry.get("food_name_malay") or "").strip(),
        str(entry.get("food_name_tamil") or "").strip(),
    ]
    aliases: list[str] = []
    for value in values:
        if value and value not in aliases:
            aliases.append(value)
    return aliases


def _normalize_aliases(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        item = normalize_text(value)
        if item and item not in normalized:
            normalized.append(item)
    return normalized


def _token_set(value: str) -> set[str]:
    normalized = normalize_text(value)
    return {token for token in normalized.split() if token}


def _overlap_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / max(1, len(left))


def _portion_unit(serving_size: str | None) -> str:
    searchable = normalize_text(serving_size or "")
    for unit in ("bowl", "plate", "cup", "piece", "glass", "portion", "set"):
        if unit in searchable:
            return unit
    return "serving"


def _default_portion_grams(serving_size: str | None, title: str) -> float:
    searchable = normalize_text(f"{serving_size or ''} {title}")
    for token, grams in (
        ("500ml", 500.0),
        ("450", 450.0),
        ("400", 400.0),
    ):
        if token in searchable:
            return grams
    unit = _portion_unit(serving_size)
    return {
        "bowl": 400.0,
        "plate": 350.0,
        "cup": 250.0,
        "glass": 250.0,
        "piece": 120.0,
        "portion": 300.0,
        "set": 450.0,
        "serving": 300.0,
    }.get(unit, 300.0)


def _portion_references(serving_size: str | None, title: str) -> list[PortionReference]:
    grams = _default_portion_grams(serving_size, title)
    return [PortionReference(unit=_portion_unit(serving_size), grams=grams, confidence=0.7)]


def _risk_tags(*, nutrition: Nutrition, preparation_tags: list[str], health_tags: list[str]) -> list[str]:
    tags = list(dict.fromkeys(str(tag).lower() for tag in health_tags if str(tag).strip()))
    if "fried" in preparation_tags and "fried" not in tags:
        tags.append("fried")
    if nutrition.sodium_mg >= 900 and "high_sodium" not in tags:
        tags.append("high_sodium")
    if nutrition.sugar_g >= 15 and "high_added_sugar" not in tags:
        tags.append("high_added_sugar")
    if nutrition.carbs_g >= 45 and nutrition.fiber_g is not None and nutrition.fiber_g < 5 and "refined_carb" not in tags:
        tags.append("refined_carb")
    if nutrition.protein_g >= 20 and "protein_rich" not in tags:
        tags.append("protein_rich")
    if (nutrition.fiber_g or 0.0) >= 5 and "fiber_rich" not in tags:
        tags.append("fiber_rich")
    if nutrition.protein_g >= 20 and (nutrition.fiber_g or 0.0) >= 5 and nutrition.sodium_mg < 900 and "balanced" not in tags:
        tags.append("balanced")
    return tags


def _number(value: object, fallback: float) -> float:
    if value is None:
        return fallback
    try:
        return float(cast(Any, value))
    except (TypeError, ValueError):
        return fallback


def _int_number(value: object, fallback: int | None) -> int | None:
    if value is None:
        return fallback
    try:
        return int(cast(Any, value))
    except (TypeError, ValueError):
        return fallback


def _from_meal_catalog_item(item: MealCatalogItem) -> CanonicalFoodRecord:
    aliases = [item.title]
    portion_references = _portion_references(item.title, item.title)
    return CanonicalFoodRecord(
        food_id=item.meal_id,
        title=item.title,
        locale=item.locale,
        aliases=aliases,
        aliases_normalized=_normalize_aliases(aliases),
        slot=item.slot,
        venue_type=item.venue_type,
        cuisine_tags=list(item.cuisine_tags),
        ingredient_tags=list(item.ingredient_tags),
        preparation_tags=list(item.preparation_tags),
        nutrition=item.nutrition,
        price_tier=item.price_tier,
        health_tags=list(item.health_tags),
        risk_tags=_risk_tags(
            nutrition=item.nutrition,
            preparation_tags=list(item.preparation_tags),
            health_tags=list(item.health_tags),
        ),
        source_dataset="default_meal_catalog",
        source_type="seed",
        default_portion_grams=_default_portion_grams(item.title, item.title),
        portion_references=portion_references,
        active=item.active,
    )


def _from_teammate_entry(entry: dict[str, object], *, base: CanonicalFoodRecord | None = None) -> CanonicalFoodRecord:
    nutrition_raw = entry.get("nutrition_per_serving") or {}
    assert isinstance(nutrition_raw, dict)
    nutrition = cast(dict[str, object], nutrition_raw)
    aliases = _aliases(entry)
    title_source = entry.get("food_name_en")
    if not title_source and base is not None:
        title_source = base.title
    title = str(title_source or "").strip()
    if not title:
        title = str(entry["food_id"])
    merged_aliases = list(dict.fromkeys([*aliases, *(base.aliases if base is not None else [])]))
    disease_advice_raw = entry.get("disease_advice") or {}
    assert isinstance(disease_advice_raw, dict)
    disease_advice = {
        str(key): CanonicalFoodAdvice.model_validate(value)
        for key, value in disease_advice_raw.items()
        if isinstance(value, dict)
    }
    alternatives_raw = cast(list[object], entry.get("healthier_alternatives") or [])
    alternatives = [
        CanonicalFoodAlternative.model_validate(item)
        for item in alternatives_raw
        if isinstance(item, dict)
    ]
    slot = base.slot if base is not None else _slot_from_category(str(entry.get("category") or ""))
    venue_type = (
        base.venue_type
        if base is not None and base.venue_type
        else normalize_text(str(entry.get("source") or "")).replace(" ", "_") or "hawker_stall"
    )
    calories = _number(nutrition.get("calories_kcal"), base.nutrition.calories if base is not None else 0)
    derived_price_tier = cast(
        "Any",
        base.price_tier if base is not None else _price_tier(str(entry.get("source") or ""), calories),
    )
    health_tags_raw = cast(list[object], entry.get("health_tags") or [])
    serving_size = str(entry.get("serving_size") or (base.serving_size if base is not None else "")) or None
    merged_health_tags = list(dict.fromkeys([*(base.health_tags if base is not None else []), *[str(item) for item in health_tags_raw]]))
    preparation_tags = list(
        dict.fromkeys([*_preparation_tags(title, str(entry.get("source") or "")), *(base.preparation_tags if base is not None else [])])
    )
    merged_nutrition = Nutrition(
        calories=calories,
        carbs_g=_number(nutrition.get("carbohydrates_g"), base.nutrition.carbs_g if base is not None else 0),
        sugar_g=_number(nutrition.get("sugar_g"), base.nutrition.sugar_g if base is not None else 0),
        protein_g=_number(nutrition.get("protein_g"), base.nutrition.protein_g if base is not None else 0),
        fat_g=_number(nutrition.get("total_fat_g"), base.nutrition.fat_g if base is not None else 0),
        sodium_mg=_number(nutrition.get("sodium_mg"), base.nutrition.sodium_mg if base is not None else 0),
        fiber_g=_number(
            nutrition.get("fiber_g"),
            base.nutrition.fiber_g if base is not None and base.nutrition.fiber_g is not None else 0,
        ),
    )
    return CanonicalFoodRecord(
        food_id=base.food_id if base is not None else f"seed.{str(entry['food_id']).lower()}",
        title=title,
        locale=base.locale if base is not None else "en-SG",
        aliases=merged_aliases,
        aliases_normalized=_normalize_aliases(merged_aliases),
        slot=slot,
        venue_type=venue_type.replace("_", " "),
        cuisine_tags=list(
            dict.fromkeys([str(entry.get("cuisine") or "").strip(), *(base.cuisine_tags if base is not None else [])])
        ),
        ingredient_tags=list(base.ingredient_tags if base is not None else []),
        preparation_tags=preparation_tags,
        nutrition=merged_nutrition,
        price_tier=derived_price_tier,
        health_tags=merged_health_tags,
        risk_tags=_risk_tags(
            nutrition=merged_nutrition,
            preparation_tags=preparation_tags,
            health_tags=merged_health_tags,
        ),
        glycemic_index_label=str(entry.get("glycemic_index") or (base.glycemic_index_label if base is not None else "")).lower() or None,
        glycemic_index_value=_int_number(entry.get("gi_value"), base.glycemic_index_value if base is not None else None),
        disease_advice=disease_advice or (base.disease_advice if base is not None else {}),
        alternatives=alternatives or (base.alternatives if base is not None else []),
        serving_size=serving_size,
        default_portion_grams=_default_portion_grams(serving_size, title),
        portion_references=_portion_references(serving_size, title),
        source_dataset="sg_hawker_food",
        source_type="import",
        localization_variant=base.localization_variant if base is not None else None,
        active=base.active if base is not None else True,
    )


def _load_teammate_seed(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def build_default_canonical_food_records() -> list[CanonicalFoodRecord]:
    """Build the full canonical food record set from all seed sources.

    NOTE: uses a lazy infra import for data loading (same pattern as domain/safety/engine.py).
    A FoodRecordRepository port would fully decouple this in a future pass.
    """
    from dietary_guardian.infrastructure.food.ingestion import (  # noqa: PLC0415
        load_open_food_facts_records,
        load_usda_records,
    )
    merged: dict[str, CanonicalFoodRecord] = {
        normalize_text(item.title): _from_meal_catalog_item(item) for item in DEFAULT_MEAL_CATALOG
    }
    for item in load_usda_records(_usda_seed_path()):
        merged.setdefault(normalize_text(item.title), item)
    for item in load_open_food_facts_records(_open_food_facts_seed_path()):
        merged.setdefault(normalize_text(item.title), item)
    for entry in _load_teammate_seed(_teammate_seed_path()):
        normalized_name = normalize_text(str(entry.get("food_name_en") or ""))
        if not normalized_name:
            continue
        merged[normalized_name] = _from_teammate_entry(entry, base=merged.get(normalized_name))
    return sorted(merged.values(), key=lambda item: item.food_id)


def rank_food_candidates(
    *,
    records: list[CanonicalFoodRecord],
    locale: str,
    observed_label: str,
    candidate_aliases: list[str] | None = None,
    detected_components: list[str] | None = None,
    preparation: str | None = None,
) -> list[tuple[CanonicalFoodRecord, float]]:
    """Rank canonical records against an observed label using name and ingredient overlap."""
    aliases = [observed_label, *(candidate_aliases or [])]
    normalized_aliases = [normalize_text(item) for item in aliases if normalize_text(item)]
    observed_tokens = set().union(*(_token_set(item) for item in normalized_aliases)) if normalized_aliases else set()
    component_tokens = {normalize_text(item) for item in (detected_components or []) if normalize_text(item)}
    preparation_token = normalize_text(preparation or "")
    ranked: list[tuple[CanonicalFoodRecord, float]] = []
    for item in records:
        if item.locale != locale or not item.active:
            continue
        record_names = [normalize_text(item.title), *item.aliases_normalized]
        name_score = 0.0
        for alias in normalized_aliases:
            if alias in record_names:
                name_score = max(name_score, 1.0)
                continue
            if any(alias in record_name or record_name in alias for record_name in record_names):
                name_score = max(name_score, 0.82)
                continue
            alias_tokens = _token_set(alias)
            record_tokens = set().union(*(_token_set(record_name) for record_name in record_names))
            name_score = max(name_score, _overlap_score(alias_tokens, record_tokens) * 0.7)
        ingredient_tokens = {normalize_text(token) for token in item.ingredient_tags if normalize_text(token)}
        component_score = _overlap_score(component_tokens, ingredient_tokens)
        prep_tokens = {normalize_text(token) for token in item.preparation_tags if normalize_text(token)}
        preparation_score = 0.0
        if preparation_token:
            if preparation_token in prep_tokens:
                preparation_score = 1.0
            elif any(preparation_token in token or token in preparation_token for token in prep_tokens):
                preparation_score = 0.65
        token_score = _overlap_score(observed_tokens, ingredient_tokens.union(prep_tokens))
        score = round(name_score * 0.65 + component_score * 0.2 + preparation_score * 0.1 + token_score * 0.05, 4)
        if score > 0:
            ranked.append((item, score))
    ranked.sort(key=lambda pair: (-pair[1], pair[0].food_id))
    return ranked


def find_food_by_name(
    records: list[CanonicalFoodRecord],
    name: str,
    *,
    locale: str = "en-SG",
) -> CanonicalFoodRecord | None:
    """Return the best-matching canonical record for a name, or ``None`` if below threshold."""
    ranked = rank_food_candidates(records=records, locale=locale, observed_label=name)
    if not ranked:
        return None
    best, score = ranked[0]
    return best if score >= 0.5 else None


__all__ = [
    "build_default_canonical_food_records",
    "find_food_by_name",
    "normalize_text",
    "rank_food_candidates",
]
