"""Temporal context builders and preference state management for recommendations.

Contains time-window helpers, slot inference utilities, ``build_temporal_context``,
and the preference-snapshot seeding / affinity-update pipeline consumed by the
orchestration layer in ``engine.py``.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from care_pilot.features.meals.domain import meal_display_name
from care_pilot.features.meals.domain.recognition import MealRecognitionRecord
from care_pilot.features.profiles.domain.models import MealSlot
from care_pilot.features.recommendations.domain.models import (
    PreferenceSnapshot,
    TemporalContext,
)
from care_pilot.features.recommendations.domain.scoring import (
    FoodItem,
    _clamp,
    _infer_slot,
    _score_similarity,
)

if TYPE_CHECKING:
    from care_pilot.features.recommendations.domain.engine import (
        RecommendationAgentRepository,
    )


def _now() -> datetime:
    return datetime.now(UTC)


def _current_slot(now: datetime | None = None) -> MealSlot:
    return _infer_slot(now or _now())


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
        matched = repository.find_food_by_name(
            locale=catalog_locale, name=meal_display_name(record)
        ) or max(
            catalog_lookup.values(),
            key=lambda item: _score_similarity(item, record),
            default=None,
        )
        weight = 0.2 + (index / max(len(meal_history), 1)) * 0.35
        if matched is not None:
            _apply_affinity_update(
                snapshot,
                candidate=matched,
                event_type="meal_logged_after_recommendation",
                weight=weight,
            )
        else:
            slot = _infer_slot(record.captured_at)
            snapshot.slot_affinity[slot] = snapshot.slot_affinity.get(slot, 0.0) + weight
    snapshot.updated_at = _now()
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
    snapshot = _snapshot_from_history(
        repository=repository,
        user_id=user_id,
        meal_history=meal_history,
        catalog=catalog,
    )
    return repository.save_preference_snapshot(snapshot)


def build_temporal_context(
    *, meal_history: list[MealRecognitionRecord], interaction_count: int
) -> TemporalContext:
    slot_counts = Counter(_infer_slot(record.captured_at) for record in meal_history)
    recent_repeat_titles = [meal_display_name(record) for record in meal_history[-3:]]
    return TemporalContext(
        current_slot=_current_slot(),
        meal_history_count=len(meal_history),
        interaction_count=interaction_count,
        recent_repeat_titles=recent_repeat_titles,
        slot_history_counts={str(key): value for key, value in slot_counts.items()},
    )
