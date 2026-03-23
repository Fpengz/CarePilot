"""Recommendation orchestration engine for daily meal plan synthesis.

This module is the public entry-point for recommendation generation.  Heavy
scoring utilities live in ``scoring.py``; temporal context and preference state
management live in ``context.py``.  Public functions defined here
(``generate_daily_agent_recommendation``, ``build_substitution_plan``,
``record_interaction_and_update_preferences``) are the only symbols that
external callers should import from this module.
"""

from __future__ import annotations

import logging
from typing import Protocol
from uuid import uuid4

from care_pilot.features.companion.core.health.models import ClinicalProfileSnapshot
from care_pilot.features.meals.domain import meal_display_name, meal_nutrition
from care_pilot.features.meals.domain.recognition import MealRecognitionRecord
from care_pilot.features.profiles.domain.health_profile import (
    compute_bmi,
    compute_profile_completeness,
)
from care_pilot.features.profiles.domain.models import MealSlot, UserProfile
from care_pilot.features.recommendations.domain.canonical_food_matching import normalize_text
from care_pilot.features.recommendations.domain.context import (
    _apply_affinity_update,
    _ensure_snapshot,
    _now,
    _snapshot_from_history,  # noqa: F401 — re-exported for callers that import from engine
    build_temporal_context,  # noqa: F401 — re-exported for callers that import from engine
)
from care_pilot.features.recommendations.domain.models import (
    AgentProfileState,
    AgentRecommendationCard,
    CandidateScores,
    DailyAgentRecommendation,
    HealthDelta,
    InteractionEventType,
    PreferenceSnapshot,
    RecommendationInteraction,
    SourceMealSummary,
    SubstitutionAlternative,
    SubstitutionPlan,
)
from care_pilot.features.recommendations.domain.scoring import (
    FoodItem,
    RankedCandidate,
    _adherence_likelihood,
    _candidate_constraints,
    _clamp,
    _health_gain,
    _infer_slot,
    _preference_fit,
    _score_similarity,
    _temporal_fit,
)

logger = logging.getLogger(__name__)

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

    def save_recommendation_interaction(
        self, interaction: RecommendationInteraction
    ) -> RecommendationInteraction: ...


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
        temporal_fit, temporal_reasons = _temporal_fit(
            candidate, temporal=temporal, meal_history=meal_history
        )
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
        adherence = _adherence_likelihood(
            snapshot, preference_fit=preference_fit, temporal_fit=temporal_fit
        )
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
    snapshot = _ensure_snapshot(
        repository=repository,
        user_id=user_id,
        meal_history=meal_history,
        catalog=catalog,
    )
    temporal = build_temporal_context(
        meal_history=meal_history, interaction_count=snapshot.interaction_count
    )
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
        confidence = _clamp(
            best.scores.total_score
            + (0.05 if snapshot.interaction_count >= INTERACTION_WARMUP_THRESHOLD else -0.05)
        )
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
    fallback_mode = (
        len(meal_history) < MEAL_LOG_WARMUP_THRESHOLD
        or snapshot.interaction_count < INTERACTION_WARMUP_THRESHOLD
    )
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
    source_catalog = repository.find_food_by_name(
        locale=health_profile.locale, name=meal_display_name(source_record)
    )
    source_slot = (
        source_catalog.slot
        if source_catalog is not None
        else _infer_slot(source_record.captured_at)
    )
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
            calories=round(
                candidate.item.nutrition.calories - source_nutrition.calories,
                2,
            ),
            sugar_g=round(candidate.item.nutrition.sugar_g - source_nutrition.sugar_g, 2),
            sodium_mg=round(
                candidate.item.nutrition.sodium_mg - source_nutrition.sodium_mg,
                2,
            ),
        )
        if not (delta.calories < 0 or delta.sugar_g < 0 or delta.sodium_mg < 0):
            continue
        taste_distance = round(
            1 - _score_similarity(candidate.item, source_catalog or source_record),
            3,
        )
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
            source_meal=SourceMealSummary(
                meal_id=source_record.id,
                title=meal_display_name(source_record),
                slot=source_slot,
            ),
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
        snapshot.adherence_bias = round(
            (snapshot.accepted_count + snapshot.swap_selected_count * 0.5)
            / snapshot.interaction_count,
            3,
        )
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
