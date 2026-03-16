"""Meal summary use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from care_pilot.core.time import local_date_for
from care_pilot.features.meals.deps import MealDeps
from care_pilot.features.meals.domain.nutrition_models import DailyNutritionSummary, NutritionTotals
from care_pilot.features.meals.domain.models import NutritionRiskProfile
from care_pilot.features.profiles.domain.health_profile import get_or_create_health_profile


@dataclass(frozen=True)
class MealWeeklySummaryData:
    week_start: str
    week_end: str
    meal_count: int
    totals: NutritionTotals
    daily_breakdown: dict[str, dict[str, float | int]]
    pattern_flags: list[str]


def get_daily_summary_data(
    *,
    deps: MealDeps,
    user_id: str,
    summary_date: date,
) -> DailyNutritionSummary:
    profile = get_or_create_health_profile(deps.stores.profiles, user_id)
    profiles = deps.stores.meals.list_nutrition_risk_profiles(user_id)
    daily = [
        item
        for item in profiles
        if local_date_for(item.captured_at, timezone_name=deps.settings.app.timezone)
        == summary_date
    ]
    calories = sum(item.calories for item in daily)
    sugar = sum(item.sugar_g for item in daily)
    sodium = sum(item.sodium_mg for item in daily)
    protein = sum(item.protein_g for item in daily)
    fiber = sum(item.fiber_g for item in daily)
    return DailyNutritionSummary(
        date=str(summary_date),
        meal_count=len(daily),
        last_logged_at=(
            max((item.captured_at for item in daily), default=None).isoformat()
            if daily
            else None
        ),
        consumed=NutritionTotals(
            calories=calories,
            sugar_g=sugar,
            sodium_mg=sodium,
            protein_g=protein,
            fiber_g=fiber,
        ),
        targets=NutritionTotals(
            calories=float(profile.target_calories_per_day or 0.0),
            sugar_g=float(profile.daily_sugar_limit_g),
            sodium_mg=float(profile.daily_sodium_limit_mg),
            protein_g=float(profile.daily_protein_target_g),
            fiber_g=float(profile.daily_fiber_target_g),
        ),
        remaining=NutritionTotals(
            calories=max(float(profile.target_calories_per_day or 0.0) - calories, 0.0),
            sugar_g=max(float(profile.daily_sugar_limit_g) - sugar, 0.0),
            sodium_mg=max(float(profile.daily_sodium_limit_mg) - sodium, 0.0),
            protein_g=max(float(profile.daily_protein_target_g) - protein, 0.0),
            fiber_g=max(float(profile.daily_fiber_target_g) - fiber, 0.0),
        ),
        insights=[],
        recommendation_hints=[],
    )


def get_weekly_summary_data(
    *,
    deps: MealDeps,
    user_id: str,
    week_start: date,
) -> MealWeeklySummaryData:
    profiles = deps.stores.meals.list_nutrition_risk_profiles(user_id)
    week_end = week_start.fromordinal(week_start.toordinal() + 6)
    week_profiles: list[NutritionRiskProfile] = []
    bucket: dict[str, list[NutritionRiskProfile]] = {}
    for item in profiles:
        day = local_date_for(item.captured_at, timezone_name=deps.settings.app.timezone)
        if day < week_start or day > week_end:
            continue
        week_profiles.append(item)
        bucket.setdefault(str(day), []).append(item)
    totals = NutritionTotals(
        calories=sum(item.calories for item in week_profiles),
        sugar_g=sum(item.sugar_g for item in week_profiles),
        sodium_mg=sum(item.sodium_mg for item in week_profiles),
        protein_g=sum(item.protein_g for item in week_profiles),
        fiber_g=sum(item.fiber_g for item in week_profiles),
    )
    breakdown = {
        day: {
            "meal_count": len(items),
            "calories": sum(item.calories for item in items),
            "sugar_g": sum(item.sugar_g for item in items),
            "sodium_mg": sum(item.sodium_mg for item in items),
        }
        for day, items in bucket.items()
    }
    return MealWeeklySummaryData(
        week_start=str(week_start),
        week_end=str(week_end),
        meal_count=sum(len(items) for items in bucket.values()),
        totals=totals,
        daily_breakdown=breakdown,
        pattern_flags=[],
    )
