"""Confirm or skip a meal candidate."""

from __future__ import annotations

from datetime import datetime, timezone

from care_pilot.features.meals.deps import MealDeps
from care_pilot.features.meals.domain.models import MealCandidateRecord


class MealCandidateNotFoundError(ValueError):
    pass


class MealCandidateInvalidStateError(ValueError):
    pass


def confirm_meal_candidate(
    *,
    deps: MealDeps,
    user_id: str,
    candidate_id: str,
    action: str,
) -> MealCandidateRecord:
    record = deps.stores.meals.get_meal_candidate(user_id, candidate_id)
    if record is None:
        raise MealCandidateNotFoundError("meal candidate not found")
    if record.confirmation_status != "pending":
        raise MealCandidateInvalidStateError("meal candidate already resolved")

    now = datetime.now(timezone.utc)
    if action == "skip":
        updated = record.model_copy(update={"confirmation_status": "skipped", "skipped_at": now})
        deps.stores.meals.save_meal_candidate(updated)
        return updated

    if action != "confirm":
        raise MealCandidateInvalidStateError("invalid confirmation action")

    if record.validated_event is None or record.nutrition_profile is None:
        raise MealCandidateInvalidStateError("candidate missing validated event or nutrition profile")

    deps.stores.meals.save_validated_meal_event(record.validated_event)
    deps.stores.meals.save_nutrition_risk_profile(record.nutrition_profile)
    updated = record.model_copy(update={"confirmation_status": "confirmed", "confirmed_at": now})
    deps.stores.meals.save_meal_candidate(updated)
    return updated
