"""Pure scoring utilities for recommendation candidate ranking.

Contains deterministic nutrient-comparison helpers, slot-baseline computation,
multi-factor preference/temporal/health scoring functions, constraint checking,
and the ``RankedCandidate`` dataclass used throughout the ranking pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp

from care_pilot.features.companion.core.health.models import (
    ClinicalProfileSnapshot,
)
from care_pilot.features.meals.domain import (
    meal_display_name,
    meal_ingredients,
    meal_nutrition,
)
from care_pilot.features.meals.domain.models import Ingredient, MealEvent
from care_pilot.features.meals.domain.recognition import MealRecognitionRecord
from care_pilot.features.profiles.domain.models import MealSlot, UserProfile
from care_pilot.features.recommendations.domain.canonical_food_matching import (
    normalize_text,
)
from care_pilot.features.recommendations.domain.models import (
    CandidateScores,
    CanonicalFoodRecord,
    HealthDelta,
    PreferenceSnapshot,
    TemporalContext,
)
from care_pilot.features.safety.domain.engine import (
    SafetyEngine,
    SafetyViolation,
)

FoodItem = CanonicalFoodRecord


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _infer_slot(captured_at: datetime) -> MealSlot:
    hour = captured_at.astimezone(timezone.utc).hour
    if 5 <= hour < 11:
        return "breakfast"
    if 11 <= hour < 16:
        return "lunch"
    if 16 <= hour < 22:
        return "dinner"
    return "snack"


def _build_meal_event(candidate: FoodItem) -> MealEvent:
    return MealEvent(
        name=candidate.title,
        ingredients=[Ingredient(name=name) for name in candidate.ingredient_tags],
        nutrition=candidate.nutrition,
    )


def _candidate_tokens(candidate: FoodItem) -> set[str]:
    venue_tokens = set(normalize_text(candidate.venue_type).split())
    return {
        normalize_text(candidate.slot),
        normalize_text(candidate.price_tier),
        *venue_tokens,
        *[normalize_text(item) for item in candidate.cuisine_tags],
        *[normalize_text(item) for item in candidate.ingredient_tags],
        *[normalize_text(item) for item in candidate.preparation_tags],
        *[normalize_text(item) for item in candidate.health_tags],
        *normalize_text(candidate.title).split(),
    }


def _record_tokens(record: MealRecognitionRecord) -> set[str]:
    return {
        *[normalize_text(item.name) for item in meal_ingredients(record)],
        *normalize_text(meal_display_name(record)).split(),
    }


def _overlap_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / max(len(left), len(right))


def _score_similarity(candidate: FoodItem, record: MealRecognitionRecord | FoodItem) -> float:
    if isinstance(record, FoodItem):
        cuisine_score = _overlap_score(set(candidate.cuisine_tags), set(record.cuisine_tags))
        ingredient_score = _overlap_score(
            set(candidate.ingredient_tags), set(record.ingredient_tags)
        )
        preparation_score = _overlap_score(
            set(candidate.preparation_tags), set(record.preparation_tags)
        )
        venue_score = 1.0 if candidate.venue_type == record.venue_type else 0.0
        slot_score = 1.0 if candidate.slot == record.slot else 0.0
        title_score = _overlap_score(
            set(normalize_text(candidate.title).split()),
            set(normalize_text(record.title).split()),
        )
    else:
        cuisine_score = 0.15 if "local" in candidate.cuisine_tags else 0.0
        ingredient_score = _overlap_score(
            set(candidate.ingredient_tags),
            {item.name.lower() for item in meal_ingredients(record)},
        )
        preparation_score = 0.0
        venue_score = 0.0
        slot_score = 1.0 if candidate.slot == _infer_slot(record.captured_at) else 0.0
        title_score = _overlap_score(
            set(normalize_text(candidate.title).split()),
            set(normalize_text(meal_display_name(record)).split()),
        )
    return _clamp(
        cuisine_score * 0.3
        + ingredient_score * 0.25
        + preparation_score * 0.1
        + venue_score * 0.15
        + slot_score * 0.1
        + title_score * 0.1
    )


def _matches_restriction(candidate: FoodItem, restricted_terms: set[str]) -> bool:
    searchable = " ".join(
        [
            candidate.title,
            *candidate.ingredient_tags,
            *candidate.cuisine_tags,
            *candidate.health_tags,
        ]
    ).lower()
    return any(term in searchable for term in restricted_terms if term)


def _slot_baseline(
    slot: str, meal_history: list[MealRecognitionRecord]
) -> tuple[float, float, float]:
    items = [
        meal_nutrition(record) for record in meal_history if _infer_slot(record.captured_at) == slot
    ]
    if not items:
        items = [meal_nutrition(record) for record in meal_history[-3:]]
    if not items:
        return (500.0, 7.0, 900.0)
    return (
        sum(item.calories for item in items) / len(items),
        sum(item.sugar_g for item in items) / len(items),
        sum(item.sodium_mg for item in items) / len(items),
    )


def _candidate_health_delta(
    candidate: FoodItem,
    *,
    slot: str,
    meal_history: list[MealRecognitionRecord],
) -> HealthDelta:
    baseline_calories, baseline_sugar, baseline_sodium = _slot_baseline(slot, meal_history)
    return HealthDelta(
        calories=round(candidate.nutrition.calories - baseline_calories, 2),
        sugar_g=round(candidate.nutrition.sugar_g - baseline_sugar, 2),
        sodium_mg=round(candidate.nutrition.sodium_mg - baseline_sodium, 2),
    )


def _preference_fit(snapshot: PreferenceSnapshot, candidate: FoodItem) -> float:
    affinity_scores: list[float] = []
    for cuisine in candidate.cuisine_tags:
        affinity_scores.append(snapshot.cuisine_affinity.get(cuisine, 0.0))
    for ingredient in candidate.ingredient_tags:
        affinity_scores.append(snapshot.ingredient_affinity.get(ingredient, 0.0))
    for tag in candidate.health_tags:
        affinity_scores.append(snapshot.health_tag_affinity.get(tag, 0.0))
    if not affinity_scores:
        return 0.5
    raw = sum(affinity_scores) / len(affinity_scores)
    return _clamp(1 / (1 + exp(-raw)))


def _temporal_fit(
    candidate: FoodItem,
    *,
    temporal: TemporalContext,
    meal_history: list[MealRecognitionRecord],
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    slot_count = temporal.slot_history_counts.get(candidate.slot, 0)
    slot_max = max(temporal.slot_history_counts.values(), default=1)
    score = slot_count / slot_max
    if slot_count:
        reasons.append(f"Matches your usual {candidate.slot} pattern.")
    normalized_title = normalize_text(candidate.title)
    if normalized_title in {normalize_text(item) for item in temporal.recent_repeat_titles}:
        score -= 0.35
        reasons.append("Down-ranked because you had this recently.")
    if not reasons:
        reasons.append("Balances variety against your usual meal timing.")
    return (_clamp(score), reasons)


def _health_gain(
    candidate: FoodItem,
    *,
    slot: MealSlot,
    meal_history: list[MealRecognitionRecord],
    snapshot: ClinicalProfileSnapshot | None,
    profile: UserProfile,
) -> tuple[float, HealthDelta, list[str]]:
    delta = _candidate_health_delta(candidate, slot=slot, meal_history=meal_history)
    reasons: list[str] = []
    score = 0.0
    if delta.sodium_mg < 0:
        score += min(
            abs(delta.sodium_mg) / max(profile.daily_sodium_limit_mg, 1.0),
            0.35,
        )
        reasons.append("Improves sodium exposure versus your recent baseline.")
    if delta.sugar_g < 0:
        score += min(abs(delta.sugar_g) / max(profile.daily_sugar_limit_g, 1.0), 0.3)
        reasons.append("Reduces sugar load compared with recent choices.")
    baseline_calories, _, _ = _slot_baseline(slot, meal_history)
    calorie_target = (
        profile.target_calories_per_day / 3
        if profile.target_calories_per_day
        else baseline_calories
    )
    if candidate.nutrition.calories <= calorie_target:
        score += 0.15
        reasons.append("Fits your current calorie pacing for this meal slot.")
    if snapshot is not None:
        biomarkers = snapshot.biomarkers
        if biomarkers.get("hba1c", 0.0) >= 7.0 and "lower_sugar" in candidate.health_tags:
            score += 0.15
        if biomarkers.get("ldl", 0.0) >= 3.4 and "heart_health" in candidate.health_tags:
            score += 0.1
        if (
            biomarkers.get("systolic_bp", 0.0) >= 140 or biomarkers.get("diastolic_bp", 0.0) >= 90
        ) and "lower_sodium" in candidate.health_tags:
            score += 0.12
    return (_clamp(score), delta, reasons)


def _adherence_likelihood(
    snapshot: PreferenceSnapshot, *, preference_fit: float, temporal_fit: float
) -> float:
    if snapshot.interaction_count <= 0:
        behavior_signal = 0.45
    else:
        behavior_signal = snapshot.accepted_count / max(snapshot.interaction_count, 1)
    return _clamp(
        preference_fit * 0.55
        + temporal_fit * 0.25
        + behavior_signal * 0.2
        + snapshot.adherence_bias * 0.05
    )


def _candidate_constraints(
    candidate: FoodItem,
    *,
    profile: UserProfile,
    restricted_terms: set[str],
) -> tuple[bool, list[str], list[str]]:
    constraints: list[str] = []
    caution_notes: list[str] = []
    if _matches_restriction(candidate, restricted_terms):
        constraints.append("excluded_restricted_term")
        return (False, constraints, caution_notes)
    if profile.budget_tier == "budget" and candidate.price_tier == "flexible":
        constraints.append("excluded_budget_mismatch")
        return (False, constraints, caution_notes)
    if candidate.nutrition.sodium_mg > profile.daily_sodium_limit_mg:
        constraints.append("excluded_high_sodium")
        return (False, constraints, caution_notes)
    if candidate.nutrition.sugar_g > profile.daily_sugar_limit_g:
        constraints.append("excluded_high_sugar")
        return (False, constraints, caution_notes)
    try:
        safety_warnings = SafetyEngine(profile).validate_meal(_build_meal_event(candidate))
        caution_notes.extend(safety_warnings)
    except SafetyViolation:
        constraints.append("excluded_safety_violation")
        return (False, constraints, caution_notes)
    return (True, constraints, caution_notes)


@dataclass
class RankedCandidate:
    item: FoodItem
    scores: CandidateScores
    reasons: list[str]
    caution_notes: list[str]
    delta: HealthDelta
