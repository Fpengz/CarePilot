"""Meal record listing helpers."""

from __future__ import annotations

from dataclasses import dataclass

from care_pilot.features.meals.deps import MealDeps
from care_pilot.features.meals.domain.models import ValidatedMealEvent


@dataclass(frozen=True)
class MealRecordsPage:
    records: list[ValidatedMealEvent]
    next_cursor: int | None
    returned: int


def list_meal_records_page(
    *,
    deps: MealDeps,
    user_id: str,
    limit: int,
    cursor: int,
) -> MealRecordsPage:
    records = deps.stores.meals.list_validated_meal_events(user_id)
    records.sort(key=lambda record: record.captured_at, reverse=True)
    start = max(cursor, 0)
    end = start + limit
    page_items = records[start:end]
    next_cursor = end if end < len(records) else None
    return MealRecordsPage(records=page_items, next_cursor=next_cursor, returned=len(page_items))
