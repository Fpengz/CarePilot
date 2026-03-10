"""Application use cases for meals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from dietary_guardian.domain.meals import (
    EnrichedMealEvent,
    MealNutritionProfile,
    MealPerception,
    MealPortionEstimate,
    NormalizedMealItem,
    PerceivedMealItem,
    PortionReference,
    RawFoodSourceRecord,
)
from dietary_guardian.domain.recommendations.canonical_food_matching import (
    normalize_text,
    rank_food_candidates,
)
from dietary_guardian.models.meal import (
    GlycemicIndexLevel,
    ImageInput,
    Ingredient,
    LocalizationDetails,
    MealState,
    Nutrition,
    PortionSize,
    VisionResult,
)
from dietary_guardian.models.meal_record import MealRecognitionRecord

_UNIT_GRAMS = {
    "bowl": 400.0,
    "cup": 250.0,
    "glass": 250.0,
    "ml": 1.0,
    "piece": 120.0,
    "plate": 350.0,
    "portion": 300.0,
    "serving": 300.0,
    "set": 450.0,
}


def _legacy_perception_from_state(state: MealState) -> MealPerception:
    amount = 1.0
    unit = "serving"
    if state.portion_size == PortionSize.SMALL:
        amount = 0.5
    elif state.portion_size == PortionSize.LARGE:
        amount = 1.5
    elif state.portion_size == PortionSize.FAMILY:
        amount = 3.0
    return MealPerception(
        meal_detected=True,
        items=[
            PerceivedMealItem(
                label=state.dish_name,
                candidate_aliases=[],
                portion_estimate=MealPortionEstimate(amount=amount, unit=unit, confidence=state.confidence_score),
                confidence=state.confidence_score,
            )
        ],
        uncertainties=list(state.visual_anomalies),
        image_quality="good" if state.confidence_score >= 0.75 else "fair",
        confidence_score=state.confidence_score,
    )


def _nutrition_scale(base: Nutrition, factor: float) -> MealNutritionProfile:
    safe_factor = max(factor, 0.0)
    return MealNutritionProfile(
        calories=float(base.calories) * safe_factor,
        carbs_g=float(base.carbs_g) * safe_factor,
        sugar_g=float(base.sugar_g) * safe_factor,
        protein_g=float(base.protein_g) * safe_factor,
        fat_g=float(base.fat_g) * safe_factor,
        sodium_mg=float(base.sodium_mg) * safe_factor,
        fiber_g=float(base.fiber_g or 0.0) * safe_factor,
    )


def _sum_nutrition(items: list[NormalizedMealItem]) -> MealNutritionProfile:
    total = MealNutritionProfile()
    for item in items:
        total.calories += item.nutrition.calories
        total.carbs_g += item.nutrition.carbs_g
        total.sugar_g += item.nutrition.sugar_g
        total.protein_g += item.nutrition.protein_g
        total.fat_g += item.nutrition.fat_g
        total.sodium_mg += item.nutrition.sodium_mg
        total.fiber_g += item.nutrition.fiber_g
    return total


def _compose_meal_name(*, normalized_items: list[NormalizedMealItem], fallback: str) -> str:
    names: list[str] = []
    for item in normalized_items:
        candidate = (item.canonical_name or item.detected_label).strip()
        if candidate and candidate not in names:
            names.append(candidate)
    if not names:
        return fallback
    if len(names) == 1:
        return names[0]
    return " + ".join(names)


def _lookup_reference(portions: list[PortionReference], unit: str) -> PortionReference | None:
    target = normalize_text(unit)
    for portion in portions:
        if normalize_text(portion.unit) == target:
            return portion
    return None


def _component_overlap(*, detected_components: list[str], ingredient_tags: list[str]) -> float:
    left = {normalize_text(item) for item in detected_components if normalize_text(item)}
    right = {normalize_text(item) for item in ingredient_tags if normalize_text(item)}
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / max(1, len(left))


def _preparation_mismatch(*, preparation: str | None, preparation_tags: list[str]) -> bool:
    target = normalize_text(preparation or "")
    if not target:
        return False
    normalized_tags = {normalize_text(item) for item in preparation_tags if normalize_text(item)}
    if not normalized_tags:
        return False
    return not any(target == item or target in item or item in target for item in normalized_tags)


def _heuristic_risk_tags(*, preparation: str | None, nutrition: MealNutritionProfile, base_tags: list[str]) -> list[str]:
    tags = list(dict.fromkeys(base_tags))
    prep = normalize_text(preparation or "")
    if "fried" in prep and "fried" not in tags:
        tags.append("fried")
    if nutrition.sodium_mg >= 900 and "high_sodium" not in tags:
        tags.append("high_sodium")
    if nutrition.sugar_g >= 15 and "high_added_sugar" not in tags:
        tags.append("high_added_sugar")
    if nutrition.carbs_g >= 45 and "refined_carb" not in tags and "higher_fiber" not in tags:
        tags.append("refined_carb")
    if nutrition.protein_g >= 20 and "protein_rich" not in tags:
        tags.append("protein_rich")
    if nutrition.fiber_g >= 5 and "fiber_rich" not in tags:
        tags.append("fiber_rich")
    if nutrition.protein_g >= 20 and nutrition.fiber_g >= 5 and nutrition.sodium_mg < 900 and "balanced" not in tags:
        tags.append("balanced")
    return tags


def _estimate_grams(*, estimate: MealPortionEstimate, default_portion_grams: float | None, portion_references: list[PortionReference]) -> float | None:
    amount = estimate.amount if estimate.amount > 0 else 1.0
    reference = _lookup_reference(portion_references, estimate.unit)
    if reference is not None and reference.grams > 0:
        return round(reference.grams * amount, 2)
    if default_portion_grams and default_portion_grams > 0:
        return round(default_portion_grams * amount, 2)
    heuristic = _UNIT_GRAMS.get(normalize_text(estimate.unit))
    if heuristic is not None:
        return round(heuristic * amount, 2)
    return None


def _portion_factor(*, estimate: MealPortionEstimate, estimated_grams: float | None, default_portion_grams: float | None) -> float:
    if estimated_grams is not None and default_portion_grams and default_portion_grams > 0:
        return estimated_grams / default_portion_grams
    return max(estimate.amount, 1.0)


def _map_portion_size(items: list[NormalizedMealItem]) -> PortionSize:
    if not items:
        return PortionSize.STANDARD
    total_amount = sum(item.portion_estimate.amount for item in items)
    if total_amount <= 0.75:
        return PortionSize.SMALL
    if total_amount >= 2.5:
        return PortionSize.FAMILY
    if total_amount >= 1.5:
        return PortionSize.LARGE
    return PortionSize.STANDARD


def _pick_glycemic_label(items: list[NormalizedMealItem], food_store: Any, locale: str) -> GlycemicIndexLevel:
    for item in items:
        if not item.canonical_name:
            continue
        matched = food_store.find_food_by_name(locale=locale, name=item.canonical_name)
        label = getattr(matched, "glycemic_index_label", None)
        if label == "low":
            return GlycemicIndexLevel.LOW
        if label == "medium":
            return GlycemicIndexLevel.MEDIUM
        if label == "high":
            return GlycemicIndexLevel.HIGH
    return GlycemicIndexLevel.UNKNOWN


def _normalize_item(*, food_store: Any, locale: str, item: Any) -> NormalizedMealItem:
    estimate = MealPortionEstimate.model_validate(item.portion_estimate)
    detected_components = list(getattr(item, "detected_components", []))
    aliases = [item.label, *item.candidate_aliases]
    records = (
        list(food_store.list_canonical_foods(locale=locale, limit=500))
        if hasattr(food_store, "list_canonical_foods")
        else []
    )
    ranked = rank_food_candidates(
        records=records,
        locale=locale,
        observed_label=item.label,
        candidate_aliases=list(item.candidate_aliases),
        detected_components=detected_components,
        preparation=item.preparation,
    )
    matched = ranked[0][0] if ranked else None
    ranking_score = ranked[0][1] if ranked else 0.0
    matched_alias = None
    strategy = "unmatched"
    confidence = 0.0
    if matched is not None:
        normalized_record_names = {normalize_text(matched.title), *getattr(matched, "aliases_normalized", [])}
        for alias in aliases:
            normalized_alias = normalize_text(alias)
            if normalized_alias in normalized_record_names:
                matched_alias = alias
                strategy = "exact_alias"
                confidence = 0.95
                break
            if any(normalized_alias in record_name or record_name in normalized_alias for record_name in normalized_record_names):
                matched_alias = alias
                strategy = "partial_alias"
                confidence = 0.82
        if matched_alias is None and ranking_score >= 0.55:
            matched_alias = item.label
            strategy = "fuzzy_alias"
            confidence = min(0.8, ranking_score)

    if matched is None:
        nutrition = MealNutritionProfile()
        tags = _heuristic_risk_tags(
            preparation=item.preparation,
            nutrition=nutrition,
            base_tags=["unmatched_food"],
        )
        return NormalizedMealItem(
            detected_label=item.label,
            canonical_name=item.label,
            match_strategy="unmatched",
            match_confidence=min(item.confidence, 0.5),
            preparation=item.preparation,
            portion_estimate=estimate,
            nutrition=nutrition,
            risk_tags=tags,
        )

    estimated_grams = _estimate_grams(
        estimate=estimate,
        default_portion_grams=getattr(matched, "default_portion_grams", None),
        portion_references=list(getattr(matched, "portion_references", [])),
    )
    factor = _portion_factor(
        estimate=estimate,
        estimated_grams=estimated_grams,
        default_portion_grams=getattr(matched, "default_portion_grams", None),
    )
    nutrition = _nutrition_scale(matched.nutrition, factor)
    tags = _heuristic_risk_tags(
        preparation=item.preparation,
        nutrition=nutrition,
        base_tags=list(getattr(matched, "risk_tags", []) or getattr(matched, "health_tags", [])),
    )
    component_overlap = _component_overlap(
        detected_components=detected_components,
        ingredient_tags=list(getattr(matched, "ingredient_tags", [])),
    )
    prep_mismatch = _preparation_mismatch(
        preparation=item.preparation,
        preparation_tags=list(getattr(matched, "preparation_tags", [])),
    )
    if detected_components and component_overlap < 0.34:
        tags.append("component_mismatch")
    if prep_mismatch:
        tags.append("component_mismatch")
    return NormalizedMealItem(
        detected_label=item.label,
        canonical_food_id=matched.food_id,
        canonical_name=matched.title,
        matched_alias=matched_alias,
        match_strategy=strategy,
        match_confidence=min(max(confidence, item.confidence, ranking_score), 1.0),
        preparation=item.preparation,
        portion_estimate=estimate,
        estimated_grams=estimated_grams,
        nutrition=nutrition,
        risk_tags=sorted(set(tags)),
        source_dataset=matched.source_dataset,
    )


def _build_legacy_state(
    *,
    prior_state: MealState,
    perception: MealPerception,
    enriched_event: EnrichedMealEvent,
    food_store: Any,
    locale: str,
    needs_manual_review: bool,
) -> MealState:
    item_names = [item.canonical_name for item in enriched_event.normalized_items if item.canonical_name]
    meal_name = enriched_event.meal_name or prior_state.dish_name
    ingredients = [Ingredient(name=name) for name in item_names[:8]]
    anomalies = list(dict.fromkeys([*perception.uncertainties, *prior_state.visual_anomalies]))
    return MealState(
        dish_name=meal_name,
        confidence_score=max(prior_state.confidence_score, perception.confidence_score),
        identification_method=prior_state.identification_method,
        ingredients=ingredients,
        nutrition=enriched_event.total_nutrition.to_legacy(),
        portion_size=_map_portion_size(enriched_event.normalized_items),
        glycemic_index_estimate=_pick_glycemic_label(enriched_event.normalized_items, food_store, locale),
        localization=LocalizationDetails(detected_components=item_names[:8]),
        visual_anomalies=anomalies,
        suggested_modifications=list(prior_state.suggested_modifications) if needs_manual_review else [],
    )


def normalize_vision_result(
    *,
    vision_result: VisionResult,
    food_store: Any,
    locale: str = "en-SG",
) -> VisionResult:
    perception = vision_result.perception or _legacy_perception_from_state(vision_result.primary_state)
    normalized_items = [_normalize_item(food_store=food_store, locale=locale, item=item) for item in perception.items]
    unresolved_items = [item.detected_label for item in normalized_items if item.match_strategy == "unmatched"]
    total_nutrition = _sum_nutrition(normalized_items)
    risk_tags = sorted({tag for item in normalized_items for tag in item.risk_tags})
    source_records = [
        RawFoodSourceRecord(source_name=item.source_dataset or "unknown", source_id=item.canonical_food_id or item.detected_label)
        for item in normalized_items
        if item.source_dataset or item.canonical_food_id
    ]
    meal_name = _compose_meal_name(
        normalized_items=normalized_items,
        fallback=vision_result.primary_state.dish_name,
    )
    needs_manual_review = bool(
        vision_result.needs_manual_review
        or unresolved_items
        or any(item.match_confidence < 0.7 for item in normalized_items)
        or any("component_mismatch" in item.risk_tags for item in normalized_items)
        or perception.image_quality == "poor"
        or (perception.image_quality == "fair" and perception.confidence_score < 0.75)
    )
    enriched_event = EnrichedMealEvent(
        meal_name=meal_name,
        normalized_items=normalized_items,
        total_nutrition=total_nutrition,
        risk_tags=risk_tags,
        unresolved_items=unresolved_items,
        source_records=source_records,
        needs_manual_review=needs_manual_review,
        summary=f"{meal_name} with {len(normalized_items)} detected item(s)",
    )
    primary_state = _build_legacy_state(
        prior_state=vision_result.primary_state,
        perception=perception,
        enriched_event=enriched_event,
        food_store=food_store,
        locale=locale,
        needs_manual_review=needs_manual_review,
    )
    return vision_result.model_copy(
        update={
            "perception": perception,
            "enriched_event": enriched_event,
            "primary_state": primary_state,
            "needs_manual_review": needs_manual_review,
        }
    )


def build_meal_record(
    *,
    image_input: Any,
    user_id: str,
    vision_result: VisionResult,
    request_id: str | None = None,
) -> MealRecognitionRecord:
    multi_item_count = max(1, len(vision_result.perception.items) if vision_result.perception else 1)
    if isinstance(image_input, ImageInput):
        raw = image_input.metadata.get("multi_item_count")
        if raw is not None:
            try:
                multi_item_count = max(multi_item_count, int(raw))
            except ValueError:
                pass
    del request_id
    return MealRecognitionRecord(
        id=str(uuid4()),
        user_id=user_id,
        captured_at=datetime.now(timezone.utc),
        source=getattr(image_input, "source", "unknown"),
        meal_state=vision_result.primary_state,
        meal_perception=vision_result.perception,
        enriched_event=vision_result.enriched_event,
        analysis_version="v2",
        multi_item_count=multi_item_count,
    )
