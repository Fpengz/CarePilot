from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from dietary_guardian.domain.identity.models import MealSlot
from dietary_guardian.domain.meals import PortionReference
from dietary_guardian.domain.recommendations.models import CanonicalFoodRecord
from dietary_guardian.models.meal import Nutrition


def _normalize_text(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return " ".join(cleaned.split())


def _nutrition_from_source(payload: dict[str, Any]) -> Nutrition:
    return Nutrition(
        calories=float(payload.get("calories", 0.0) or 0.0),
        carbs_g=float(payload.get("carbs_g", 0.0) or 0.0),
        sugar_g=float(payload.get("sugar_g", 0.0) or 0.0),
        protein_g=float(payload.get("protein_g", 0.0) or 0.0),
        fat_g=float(payload.get("fat_g", 0.0) or 0.0),
        sodium_mg=float(payload.get("sodium_mg", 0.0) or 0.0),
        fiber_g=float(payload.get("fiber_g", 0.0) or 0.0),
    )


def _risk_tags(nutrition: Nutrition) -> list[str]:
    tags: list[str] = []
    if nutrition.sodium_mg >= 900:
        tags.append("high_sodium")
    if nutrition.sugar_g >= 15:
        tags.append("high_added_sugar")
    if nutrition.protein_g >= 20:
        tags.append("protein_rich")
    if (nutrition.fiber_g or 0.0) >= 5:
        tags.append("fiber_rich")
    return tags


def _read_json_array(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [cast(dict[str, Any], item) for item in raw if isinstance(item, dict)]


def _portion(unit: str, grams: float) -> list[PortionReference]:
    return [PortionReference(unit=unit, grams=grams, confidence=0.6)]


def _slot(value: str) -> MealSlot:
    normalized = value.strip().lower()
    if normalized in {"breakfast", "lunch", "dinner", "snack"}:
        return cast(MealSlot, normalized)
    return "lunch"


def _scale_nutrition(nutrition: Nutrition, factor: float) -> Nutrition:
    return Nutrition(
        calories=round(nutrition.calories * factor, 4),
        carbs_g=round(nutrition.carbs_g * factor, 4),
        sugar_g=round(nutrition.sugar_g * factor, 4),
        protein_g=round(nutrition.protein_g * factor, 4),
        fat_g=round(nutrition.fat_g * factor, 4),
        sodium_mg=round(nutrition.sodium_mg * factor, 4),
        fiber_g=round((nutrition.fiber_g or 0.0) * factor, 4),
    )


def load_usda_records(path: Path) -> list[CanonicalFoodRecord]:
    records: list[CanonicalFoodRecord] = []
    for entry in _read_json_array(path):
        title = str(entry.get("description") or "").strip()
        if not title:
            continue
        nutrients = cast(dict[str, Any], entry.get("nutrients") or {})
        nutrition = _nutrition_from_source(
            {
                "calories": nutrients.get("calories"),
                "carbs_g": nutrients.get("carbohydrates"),
                "sugar_g": nutrients.get("sugars"),
                "protein_g": nutrients.get("protein"),
                "fat_g": nutrients.get("fat"),
                "sodium_mg": nutrients.get("sodium"),
                "fiber_g": nutrients.get("fiber"),
            }
        )
        aliases = [title, *[str(item) for item in cast(list[Any], entry.get("aliases") or []) if str(item).strip()]]
        records.append(
            CanonicalFoodRecord(
                food_id=f"usda.{entry.get('fdc_id')}",
                title=title,
                aliases=aliases,
                aliases_normalized=[_normalize_text(item) for item in aliases],
                slot=_slot(str(entry.get("slot") or "lunch")),
                venue_type=str(entry.get("venue_type") or "source import"),
                cuisine_tags=[str(entry.get("cuisine") or "global")],
                preparation_tags=[str(entry.get("preparation") or "prepared")],
                nutrition=nutrition,
                health_tags=_risk_tags(nutrition),
                risk_tags=_risk_tags(nutrition),
                source_dataset="usda_fooddata_central",
                source_type="import",
                serving_size=str(entry.get("serving_size") or "1 serving"),
                default_portion_grams=float(entry.get("default_portion_grams") or 100.0),
                portion_references=_portion(str(entry.get("portion_unit") or "serving"), float(entry.get("default_portion_grams") or 100.0)),
            )
        )
    return records


def load_open_food_facts_records(path: Path) -> list[CanonicalFoodRecord]:
    records: list[CanonicalFoodRecord] = []
    for entry in _read_json_array(path):
        title = str(entry.get("product_name") or "").strip()
        if not title:
            continue
        nutriments = cast(dict[str, Any], entry.get("nutriments") or {})
        default_portion_grams = float(entry.get("serving_quantity") or 100.0)
        nutrition = _scale_nutrition(
            _nutrition_from_source(
                {
                    "calories": nutriments.get("energy-kcal_100g"),
                    "carbs_g": nutriments.get("carbohydrates_100g"),
                    "sugar_g": nutriments.get("sugars_100g"),
                    "protein_g": nutriments.get("proteins_100g"),
                    "fat_g": nutriments.get("fat_100g"),
                    "sodium_mg": float(nutriments.get("salt_100g", 0.0) or 0.0) * 400.0,
                    "fiber_g": nutriments.get("fiber_100g"),
                }
            ),
            max(default_portion_grams, 0.0) / 100.0,
        )
        aliases = [title, str(entry.get("generic_name") or "").strip()]
        aliases = [item for item in aliases if item]
        category = str(entry.get("category") or "snack")
        records.append(
            CanonicalFoodRecord(
                food_id=f"off.{entry.get('code')}",
                title=title,
                aliases=aliases,
                aliases_normalized=[_normalize_text(item) for item in aliases],
                slot="snack" if "drink" in _normalize_text(category) or "snack" in _normalize_text(category) else "lunch",
                venue_type="packaged food",
                cuisine_tags=["packaged"],
                preparation_tags=["packaged"],
                nutrition=nutrition,
                health_tags=_risk_tags(nutrition),
                risk_tags=_risk_tags(nutrition),
                source_dataset="open_food_facts",
                source_type="import",
                serving_size=str(entry.get("serving_size") or "100 g"),
                default_portion_grams=default_portion_grams,
                portion_references=_portion("serving", default_portion_grams),
            )
        )
    return records
