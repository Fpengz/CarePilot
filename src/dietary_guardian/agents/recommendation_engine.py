"""Recommendation scoring and orchestration engine for daily meal plan synthesis.

Contains deterministic scoring utilities, preference tracking, temporal context building,
and the main ``generate_daily_agent_recommendation`` / ``build_substitution_plan`` entry-points
consumed by the recommendation agent facade.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp
from typing import Protocol
from uuid import uuid4

from dietary_guardian.domain.health.models import ClinicalProfileSnapshot
from dietary_guardian.domain.identity.models import MealSlot, UserProfile
from dietary_guardian.domain.recommendations.models import (
    AgentProfileState,
    AgentRecommendationCard,
    CandidateScores,
    CanonicalFoodRecord,
    DailyAgentRecommendation,
    HealthDelta,
    InteractionEventType,
    PreferenceSnapshot,
    RecommendationInteraction,
    SourceMealSummary,
    SubstitutionAlternative,
    SubstitutionPlan,
    TemporalContext,
)
from dietary_guardian.observability import get_logger
from dietary_guardian.models.meal import Ingredient, MealEvent
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.safety.engine import SafetyEngine, SafetyViolation
from dietary_guardian.domain.nutrition import (
    meal_display_name,
    meal_ingredients,
    meal_nutrition,
)
from dietary_guardian.domain.profiles.health_profile import (
    compute_bmi,
    compute_profile_completeness,
)
from dietary_guardian.domain.recommendations.canonical_food_matching import normalize_text

logger = get_logger(__name__)
FoodItem = CanonicalFoodRecord

MEAL_LOG_WARMUP_THRESHOLD = 10
INTERACTION_WARMUP_THRESHOLD = 5


class AgentMealNotFoundError(Exception):
    pass


class RecommendationAgentRepository(Protocol):
    def list_canonical_foods(
        self,
        *,
        locale: str,
        slot: str | None = None,
        limit: int = 100,
    ) -> list[FoodItem]: ...

    def get_preference_snapshot(self, user_id: str) -> PreferenceSnapshot | None: ...

    def save_preference_snapshot(self, snapshot: PreferenceSnapshot) -> PreferenceSnapshot: ...

    def get_meal_record(self, user_id: str, meal_id: str) -> MealRecognitionRecord | None: ...

    def get_canonical_food(self, food_id: str) -> FoodItem | None: ...

    def find_food_by_name(self, *, locale: str, name: str) -> FoodItem | None: ...

    def save_recommendation_interaction(self, interaction: RecommendationInteraction) -> RecommendationInteraction: ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
        ingredient_score = _overlap_score(set(candidate.ingredient_tags), set(record.ingredient_tags))
        preparation_score = _overlap_score(set(candidate.preparation_tags), set(record.preparation_tags))
        venue_score = 1.0 if candidate.venue_type == record.venue_type else 0.0
        slot_score = 1.0 if candidate.slot == record.slot else 0.0
        title_score = _overlap_score(set(normalize_text(candidate.title).split()), set(normalize_text(record.title).split()))
    else:
        cuisine_score = 0.15 if "local" in candidate.cuisine_tags else 0.0
        ingredient_score = _overlap_score(set(candidate.ingredient_tags), {item.name.lower() for item in meal_ingredients(record)})
        preparation_score = 0.0
        venue_score = 0.0
        slot_score = 1.0 if candidate.slot == _infer_slot(record.captured_at) else 0.0
        title_score = _overlap_score(set(normalize_text(candidate.title).split()), set(normalize_text(meal_display_name(record)).split()))
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


def _slot_baseline(slot: str, meal_history: list[MealRecognitionRecord]) -> tuple[float, float, float]:
    items = [meal_nutrition(record) for record in meal_history if _infer_slot(record.captured_at) == slot]
    if not items:
        items = [meal_nutrition(record) for record in meal_history[-3:]]
    if not items:
        return (500.0, 7.0, 900.0)
    return (
        sum(item.calories for item in items) / len(items),
        sum(item.sugar_g for item in items) / len(items),
        sum(item.sodium_mg for item in items) / len(items),
    )


def _candidate_health_delta(candidate: FoodItem, *, slot: str, meal_history: list[MealRecognitionRecord]) -> HealthDelta:
    baseline_calories, baseline_sugar, baseline_sodium = _slot_baseline(slot, meal_history)
    return HealthDelta(
        calories=round(candidate.nutrition.calories - baseline_calories, 2),
        sugar_g=round(candidate.nutrition.sugar_g - baseline_sugar, 2),
        sodium_mg=round(candidate.nutrition.sodium_mg - baseline_sodium, 2),
    )


def _current_slot(now: datetime | None = None) -> MealSlot:
    return _infer_slot(now or _now())


def _snapshot_from_history(
    *,
    repository: RecommendationAgentRepository,
    user_id: str,
    meal_history: list[MealRecognitionRecord],
    catalog: list[FoodItem],
) -> PreferenceSnapshot:
    snapshot = PreferenceSnapshot(user_id=user_id)
    catalog_lookup = {item.meal_id: item for item in catalog}
    catalog_locale = next((item.locale for item in catalog if item.locale), "en-SG")
    for index, record in enumerate(meal_history, start=1):
        matched = repository.find_food_by_name(locale=catalog_locale, name=meal_display_name(record)) or max(
            catalog_lookup.values(),
            key=lambda item: _score_similarity(item, record),
            default=None,
        )
        weight = 0.2 + (index / max(len(meal_history), 1)) * 0.35
        if matched is not None:
            _apply_affinity_update(snapshot, candidate=matched, event_type="meal_logged_after_recommendation", weight=weight)
        else:
            slot = _infer_slot(record.captured_at)
            snapshot.slot_affinity[slot] = snapshot.slot_affinity.get(slot, 0.0) + weight
    snapshot.updated_at = _now()
    return snapshot


def _apply_weight(values: dict[str, float], key: str, weight: float) -> None:
    values[key] = round(values.get(key, 0.0) * 0.9 + weight, 4)


def _apply_affinity_update(
    snapshot: PreferenceSnapshot,
    *,
    candidate: FoodItem,
    event_type: str,
    weight: float | None = None,
) -> PreferenceSnapshot:
    event_weight = weight
    if event_weight is None:
        event_weight = {
            "viewed": 0.1,
            "accepted": 1.0,
            "dismissed": -0.45,
            "swap_selected": 0.85,
            "meal_logged_after_recommendation": 1.2,
            "ignored": -0.1,
        }.get(event_type, 0.0)
    for cuisine in candidate.cuisine_tags:
        _apply_weight(snapshot.cuisine_affinity, cuisine, event_weight)
    for ingredient in candidate.ingredient_tags:
        _apply_weight(snapshot.ingredient_affinity, ingredient, event_weight * 0.7)
    for tag in candidate.health_tags:
        _apply_weight(snapshot.health_tag_affinity, tag, event_weight * 0.6)
    _apply_weight(snapshot.slot_affinity, candidate.slot, event_weight)
    if event_type in {"accepted", "meal_logged_after_recommendation"}:
        snapshot.accepted_count += 1
    if event_type == "dismissed":
        snapshot.dismissed_count += 1
    if event_type == "swap_selected":
        snapshot.swap_selected_count += 1
        snapshot.substitution_tolerance = _clamp(snapshot.substitution_tolerance + 0.03, 0.2, 0.95)
    if event_type == "dismissed":
        snapshot.substitution_tolerance = _clamp(snapshot.substitution_tolerance - 0.02, 0.2, 0.95)
    return snapshot


def _ensure_snapshot(
    *,
    repository: RecommendationAgentRepository,
    user_id: str,
    meal_history: list[MealRecognitionRecord],
    catalog: list[FoodItem],
) -> PreferenceSnapshot:
    stored = repository.get_preference_snapshot(user_id)
    if stored is not None:
        return stored
    snapshot = _snapshot_from_history(repository=repository, user_id=user_id, meal_history=meal_history, catalog=catalog)
    return repository.save_preference_snapshot(snapshot)


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


def _temporal_fit(candidate: FoodItem, *, temporal: TemporalContext, meal_history: list[MealRecognitionRecord]) -> tuple[float, list[str]]:
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
        score += min(abs(delta.sodium_mg) / max(profile.daily_sodium_limit_mg, 1.0), 0.35)
        reasons.append("Improves sodium exposure versus your recent baseline.")
    if delta.sugar_g < 0:
        score += min(abs(delta.sugar_g) / max(profile.daily_sugar_limit_g, 1.0), 0.3)
        reasons.append("Reduces sugar load compared with recent choices.")
    baseline_calories, _, _ = _slot_baseline(slot, meal_history)
    calorie_target = profile.target_calories_per_day / 3 if profile.target_calories_per_day else baseline_calories
    if candidate.nutrition.calories <= calorie_target:
        score += 0.15
        reasons.append("Fits your current calorie pacing for this meal slot.")
    if snapshot is not None:
        biomarkers = snapshot.biomarkers
        if biomarkers.get("hba1c", 0.0) >= 7.0 and "lower_sugar" in candidate.health_tags:
            score += 0.15
        if biomarkers.get("ldl", 0.0) >= 3.4 and "heart_health" in candidate.health_tags:
            score += 0.1
        if (biomarkers.get("systolic_bp", 0.0) >= 140 or biomarkers.get("diastolic_bp", 0.0) >= 90) and "lower_sodium" in candidate.health_tags:
            score += 0.12
    return (_clamp(score), delta, reasons)


def _adherence_likelihood(snapshot: PreferenceSnapshot, *, preference_fit: float, temporal_fit: float) -> float:
    if snapshot.interaction_count <= 0:
        behavior_signal = 0.45
    else:
        behavior_signal = snapshot.accepted_count / max(snapshot.interaction_count, 1)
    return _clamp(preference_fit * 0.55 + temporal_fit * 0.25 + behavior_signal * 0.2 + snapshot.adherence_bias * 0.05)


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


def _rank_candidates_for_slot(
    *,
    slot: MealSlot,
    catalog: list[FoodItem],
    snapshot: PreferenceSnapshot,
    meal_history: list[MealRecognitionRecord],
    clinical_snapshot: ClinicalProfileSnapshot | None,
    profile: UserProfile,
    restricted_terms: set[str],
    source_meal: MealRecognitionRecord | FoodItem | None = None,
) -> tuple[list[RankedCandidate], list[str]]:
    temporal = build_temporal_context(
        meal_history=meal_history,
        interaction_count=snapshot.interaction_count,
    )
    constraints_applied: list[str] = []
    ranked: list[RankedCandidate] = []
    slot_catalog = [item for item in catalog if item.slot == slot]
    for candidate in slot_catalog:
        allowed, constraints, caution_notes = _candidate_constraints(
            candidate,
            profile=profile,
            restricted_terms=restricted_terms,
        )
        if not allowed:
            constraints_applied.extend(constraints)
            continue
        preference_fit = _preference_fit(snapshot, candidate)
        temporal_fit, temporal_reasons = _temporal_fit(candidate, temporal=temporal, meal_history=meal_history)
        health_gain, delta, health_reasons = _health_gain(
            candidate,
            slot=slot,
            meal_history=meal_history,
            snapshot=clinical_snapshot,
            profile=profile,
        )
        source_for_distance = source_meal or (meal_history[-1] if meal_history else None)
        if source_for_distance is None:
            substitution_penalty = 0.12
        else:
            substitution_penalty = round(1 - _score_similarity(candidate, source_for_distance), 3)
        adherence = _adherence_likelihood(snapshot, preference_fit=preference_fit, temporal_fit=temporal_fit)
        total = (
            preference_fit * 0.35
            + temporal_fit * 0.20
            + adherence * 0.20
            + health_gain * 0.20
            - substitution_penalty * 0.05
        )
        scores = CandidateScores(
            preference_fit=round(preference_fit, 3),
            temporal_fit=round(temporal_fit, 3),
            adherence_likelihood=round(adherence, 3),
            health_gain=round(health_gain, 3),
            substitution_deviation_penalty=round(substitution_penalty, 3),
            total_score=round(total, 3),
        )
        ranked.append(
            RankedCandidate(
                item=candidate,
                scores=scores,
                reasons=[*temporal_reasons, *health_reasons],
                caution_notes=caution_notes,
                delta=delta,
            )
        )
    ranked.sort(key=lambda item: item.scores.total_score, reverse=True)
    return (ranked, sorted(set(constraints_applied)))


def build_temporal_context(*, meal_history: list[MealRecognitionRecord], interaction_count: int) -> TemporalContext:
    slot_counts = Counter(_infer_slot(record.captured_at) for record in meal_history)
    recent_repeat_titles = [meal_display_name(record) for record in meal_history[-3:]]
    return TemporalContext(
        current_slot=_current_slot(),
        meal_history_count=len(meal_history),
        interaction_count=interaction_count,
        recent_repeat_titles=recent_repeat_titles,
        slot_history_counts={str(key): value for key, value in slot_counts.items()},
    )


def generate_daily_agent_recommendation(
    *,
    repository: RecommendationAgentRepository,
    user_id: str,
    health_profile,
    user_profile: UserProfile,
    meal_history: list[MealRecognitionRecord],
    clinical_snapshot: ClinicalProfileSnapshot | None,
) -> DailyAgentRecommendation:
    catalog = repository.list_canonical_foods(locale=health_profile.locale)
    snapshot = _ensure_snapshot(repository=repository, user_id=user_id, meal_history=meal_history, catalog=catalog)
    temporal = build_temporal_context(meal_history=meal_history, interaction_count=snapshot.interaction_count)
    restricted_terms = {
        *[item.lower() for item in health_profile.allergies],
        *[item.lower() for item in health_profile.disliked_ingredients],
    }
    recommendations: dict[str, AgentRecommendationCard] = {}
    constraints_applied: list[str] = []
    for slot in ("breakfast", "lunch", "dinner", "snack"):
        ranked, filtered_constraints = _rank_candidates_for_slot(
            slot=slot,
            catalog=catalog,
            snapshot=snapshot,
            meal_history=meal_history,
            clinical_snapshot=clinical_snapshot,
            profile=user_profile,
            restricted_terms=restricted_terms,
        )
        constraints_applied.extend(filtered_constraints)
        if not ranked:
            continue
        best = ranked[0]
        confidence = _clamp(best.scores.total_score + (0.05 if snapshot.interaction_count >= INTERACTION_WARMUP_THRESHOLD else -0.05))
        recommendations[slot] = AgentRecommendationCard(
            candidate_id=best.item.meal_id,
            slot=slot,
            title=best.item.title,
            venue_type=best.item.venue_type,
            why_it_fits=best.reasons,
            caution_notes=best.caution_notes,
            confidence=round(confidence, 2),
            scores=best.scores,
            health_gain_summary=best.delta,
        )

    substitutions = build_substitution_plan(
        repository=repository,
        user_id=user_id,
        health_profile=health_profile,
        user_profile=user_profile,
        meal_history=meal_history,
        clinical_snapshot=clinical_snapshot,
        source_meal_id=(meal_history[-1].id if meal_history else None),
        limit=2,
    )
    completeness = compute_profile_completeness(health_profile)
    fallback_mode = len(meal_history) < MEAL_LOG_WARMUP_THRESHOLD or snapshot.interaction_count < INTERACTION_WARMUP_THRESHOLD
    recommendation = DailyAgentRecommendation(
        profile_state=AgentProfileState(
            completeness_state=completeness.state,
            bmi=compute_bmi(health_profile),
            target_calories_per_day=health_profile.target_calories_per_day,
            macro_focus=list(health_profile.macro_focus),
        ),
        temporal_context=temporal,
        recommendations=recommendations,
        substitutions=substitutions,
        fallback_mode=fallback_mode,
        data_sources={
            "meal_history_count": len(meal_history),
            "interaction_count": snapshot.interaction_count,
            "has_preference_snapshot": True,
            "has_clinical_snapshot": clinical_snapshot is not None,
        },
        constraints_applied=sorted(set(constraints_applied)),
    )
    logger.info(
        "agent_recommendation_complete user_id=%s fallback_mode=%s interactions=%s recommendations=%s",
        user_id,
        recommendation.fallback_mode,
        snapshot.interaction_count,
        sorted(recommendation.recommendations.keys()),
    )
    return recommendation


def build_substitution_plan(
    *,
    repository: RecommendationAgentRepository,
    user_id: str,
    health_profile,
    user_profile: UserProfile,
    meal_history: list[MealRecognitionRecord],
    clinical_snapshot: ClinicalProfileSnapshot | None,
    source_meal_id: str | None,
    limit: int,
) -> SubstitutionPlan | None:
    if source_meal_id is None:
        if not meal_history:
            return None
        source_record = meal_history[-1]
    else:
        source_record = repository.get_meal_record(user_id, source_meal_id)
        if source_record is None:
            raise AgentMealNotFoundError(source_meal_id)
    source_catalog = repository.find_food_by_name(locale=health_profile.locale, name=meal_display_name(source_record))
    source_slot = source_catalog.slot if source_catalog is not None else _infer_slot(source_record.captured_at)
    catalog = repository.list_canonical_foods(locale=health_profile.locale, slot=source_slot)
    snapshot = _ensure_snapshot(
        repository=repository,
        user_id=user_id,
        meal_history=meal_history,
        catalog=catalog or repository.list_canonical_foods(locale=health_profile.locale),
    )
    restricted_terms = {
        *[item.lower() for item in health_profile.allergies],
        *[item.lower() for item in health_profile.disliked_ingredients],
    }
    ranked, _ = _rank_candidates_for_slot(
        slot=source_slot,
        catalog=catalog,
        snapshot=snapshot,
        meal_history=meal_history,
        clinical_snapshot=clinical_snapshot,
        profile=user_profile,
        restricted_terms=restricted_terms,
        source_meal=source_catalog or source_record,
    )
    alternatives: list[SubstitutionAlternative] = []
    source_nutrition = meal_nutrition(source_record)
    for candidate in ranked:
        if normalize_text(candidate.item.title) == normalize_text(meal_display_name(source_record)):
            continue
        delta = HealthDelta(
            calories=round(candidate.item.nutrition.calories - source_nutrition.calories, 2),
            sugar_g=round(candidate.item.nutrition.sugar_g - source_nutrition.sugar_g, 2),
            sodium_mg=round(candidate.item.nutrition.sodium_mg - source_nutrition.sodium_mg, 2),
        )
        if not (delta.calories < 0 or delta.sugar_g < 0 or delta.sodium_mg < 0):
            continue
        taste_distance = round(1 - _score_similarity(candidate.item, source_catalog or source_record), 3)
        if taste_distance > max(snapshot.substitution_tolerance, 0.75):
            continue
        alternatives.append(
            SubstitutionAlternative(
                candidate_id=candidate.item.meal_id,
                title=candidate.item.title,
                venue_type=candidate.item.venue_type,
                health_delta=delta,
                taste_distance=taste_distance,
                reasoning="A healthier local alternative that stays close to your familiar taste profile.",
                confidence=round(_clamp(candidate.scores.total_score), 2),
            )
        )
        if len(alternatives) >= limit:
            break
    if not alternatives:
        return SubstitutionPlan(
            source_meal=SourceMealSummary(meal_id=source_record.id, title=meal_display_name(source_record), slot=source_slot),
            blocked_reason="No healthier low-deviation substitution was available for this meal.",
        )
    return SubstitutionPlan(
        source_meal=SourceMealSummary(
            meal_id=source_record.id,
            title=meal_display_name(source_record),
            slot=source_slot,
        ),
        alternatives=alternatives,
    )


def record_interaction_and_update_preferences(
    *,
    repository: RecommendationAgentRepository,
    user_id: str,
    candidate_id: str,
    recommendation_id: str,
    event_type: InteractionEventType,
    slot: MealSlot,
    source_meal_id: str | None,
    selected_meal_id: str | None,
    metadata: dict[str, object],
    meal_history: list[MealRecognitionRecord],
) -> tuple[RecommendationInteraction, PreferenceSnapshot]:
    candidate = repository.get_canonical_food(candidate_id)
    if candidate is None:
        raise AgentMealNotFoundError(candidate_id)
    snapshot = _ensure_snapshot(
        repository=repository,
        user_id=user_id,
        meal_history=meal_history,
        catalog=repository.list_canonical_foods(locale=candidate.locale),
    )
    snapshot.interaction_count += 1
    _apply_affinity_update(snapshot, candidate=candidate, event_type=event_type)
    snapshot.updated_at = _now()
    if snapshot.interaction_count > 0:
        snapshot.adherence_bias = round((snapshot.accepted_count + snapshot.swap_selected_count * 0.5) / snapshot.interaction_count, 3)
    interaction = RecommendationInteraction(
        interaction_id=str(uuid4()),
        user_id=user_id,
        recommendation_id=recommendation_id,
        candidate_id=candidate_id,
        event_type=event_type,
        slot=slot,
        source_meal_id=source_meal_id,
        selected_meal_id=selected_meal_id,
        metadata=metadata,
    )
    repository.save_recommendation_interaction(interaction)
    repository.save_preference_snapshot(snapshot)
    logger.info(
        "interaction_learning_complete user_id=%s candidate_id=%s event_type=%s interactions=%s",
        user_id,
        candidate_id,
        event_type,
        snapshot.interaction_count,
    )
    return (interaction, snapshot)
