"""Weekly nutrition summary calculations for meal history review.

Moved from domain.nutrition — now part of domain.meals.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

from dietary_guardian.domain.meals.recognition import MealRecognitionRecord
from dietary_guardian.shared.time import local_date_for

from .meal_record_accessors import meal_display_name, meal_nutrition


def _week_end(week_start: date) -> date:
    return week_start + timedelta(days=6)


def build_weekly_nutrition_summary(
    *,
    meal_history: list[MealRecognitionRecord],
    week_start: date,
    timezone_name: str = "UTC",
) -> dict[str, object]:
    week_end = _week_end(week_start)
    week_records = [
        item
        for item in meal_history
        if week_start <= local_date_for(item.captured_at, timezone_name=timezone_name) <= week_end
    ]
    totals = {
        "calories": 0.0,
        "sugar_g": 0.0,
        "sodium_mg": 0.0,
        "protein_g": 0.0,
        "fiber_g": 0.0,
    }
    daily_breakdown: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"meal_count": 0, "calories": 0.0, "sugar_g": 0.0, "sodium_mg": 0.0}
    )
    repeats = Counter()
    for record in week_records:
        nutrition = meal_nutrition(record)
        totals["calories"] += float(nutrition.calories)
        totals["sugar_g"] += float(nutrition.sugar_g)
        totals["sodium_mg"] += float(nutrition.sodium_mg)
        totals["protein_g"] += float(nutrition.protein_g)
        totals["fiber_g"] += float(nutrition.fiber_g or 0.0)
        day_key = local_date_for(record.captured_at, timezone_name=timezone_name).isoformat()
        bucket = daily_breakdown[day_key]
        meal_count = int(bucket.get("meal_count", 0))
        calories = float(bucket.get("calories", 0.0))
        sugar_g = float(bucket.get("sugar_g", 0.0))
        sodium_mg = float(bucket.get("sodium_mg", 0.0))
        bucket["meal_count"] = meal_count + 1
        bucket["calories"] = calories + float(nutrition.calories)
        bucket["sugar_g"] = sugar_g + float(nutrition.sugar_g)
        bucket["sodium_mg"] = sodium_mg + float(nutrition.sodium_mg)
        repeats[meal_display_name(record).lower().strip()] += 1
    pattern_flags: list[str] = []
    if any(count >= 3 for count in repeats.values()):
        pattern_flags.append("repetitive_meals")
    if totals["sodium_mg"] > 14000:
        pattern_flags.append("high_weekly_sodium")
    if totals["sugar_g"] > 210:
        pattern_flags.append("high_weekly_sugar")
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "meal_count": len(week_records),
        "totals": {key: round(value, 4) for key, value in totals.items()},
        "daily_breakdown": dict(daily_breakdown),
        "pattern_flags": pattern_flags,
    }
