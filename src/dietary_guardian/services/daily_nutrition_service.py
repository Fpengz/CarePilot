from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

from dietary_guardian.models.daily_nutrition import DailyNutritionSummary, NutritionInsight, NutritionTotals
from dietary_guardian.models.health_profile import HealthProfileRecord
from dietary_guardian.models.meal_record import MealRecognitionRecord


def build_daily_nutrition_summary(
    *,
    profile: HealthProfileRecord,
    meal_history: list[MealRecognitionRecord],
    summary_date: date,
) -> DailyNutritionSummary:
    day_records = [record for record in meal_history if record.captured_at.date() == summary_date]
    consumed = _sum_records(day_records)
    targets = NutritionTotals(
        calories=float(profile.target_calories_per_day or 0.0),
        sugar_g=float(profile.daily_sugar_limit_g),
        sodium_mg=float(profile.daily_sodium_limit_mg),
        protein_g=float(profile.daily_protein_target_g),
        fiber_g=float(profile.daily_fiber_target_g),
    )
    remaining = NutritionTotals(
        calories=max(targets.calories - consumed.calories, 0.0),
        sugar_g=max(targets.sugar_g - consumed.sugar_g, 0.0),
        sodium_mg=max(targets.sodium_mg - consumed.sodium_mg, 0.0),
        protein_g=max(targets.protein_g - consumed.protein_g, 0.0),
        fiber_g=max(targets.fiber_g - consumed.fiber_g, 0.0),
    )
    insights = _build_insights(profile=profile, meal_history=meal_history, summary_date=summary_date)
    return DailyNutritionSummary(
        date=summary_date.isoformat(),
        meal_count=len(day_records),
        last_logged_at=day_records[-1].captured_at.isoformat() if day_records else None,
        consumed=consumed,
        targets=targets,
        remaining=remaining,
        insights=insights,
        recommendation_hints=_recommendation_hints(insights),
    )


def _sum_records(records: list[MealRecognitionRecord]) -> NutritionTotals:
    totals = NutritionTotals()
    for record in records:
        nutrition = record.meal_state.nutrition
        totals.calories += float(nutrition.calories)
        totals.sugar_g += float(nutrition.sugar_g)
        totals.sodium_mg += float(nutrition.sodium_mg)
        totals.protein_g += float(nutrition.protein_g)
        totals.fiber_g += float(nutrition.fiber_g or 0.0)
    return NutritionTotals.model_validate(totals.model_dump(mode="json"))


def _normalize_dish_name(value: str) -> str:
    return " ".join(value.lower().split())


def _build_insights(
    *,
    profile: HealthProfileRecord,
    meal_history: list[MealRecognitionRecord],
    summary_date: date,
) -> list[NutritionInsight]:
    window_start = summary_date - timedelta(days=6)
    window_records = [
        record
        for record in meal_history
        if window_start <= record.captured_at.date() <= summary_date
    ]
    distinct_days = {record.captured_at.date().isoformat() for record in window_records}
    if len(window_records) < 5 or len(distinct_days) < 3:
        return []

    insights: list[NutritionInsight] = []
    average_protein = sum(record.meal_state.nutrition.protein_g for record in window_records) / len(window_records)
    protein_dense_share = (
        sum(1 for record in window_records if record.meal_state.nutrition.protein_g >= 20.0) / len(window_records)
    )
    if average_protein < 18.0 or protein_dense_share < 0.4:
        insights.append(
            NutritionInsight(
                code="low_protein_pattern",
                title="Protein intake may be running low",
                summary="Possible low-protein pattern based on your recent meals. Adding lean protein could improve meal balance.",
                actions=["Choose meals with tofu, eggs, fish, or chicken.", "Pair carb-heavy dishes with a higher-protein side."],
            )
        )

    average_fiber = sum(float(record.meal_state.nutrition.fiber_g or 0.0) for record in window_records) / len(window_records)
    if average_fiber < 5.0:
        insights.append(
            NutritionInsight(
                code="low_fiber_pattern",
                title="Fiber intake looks light",
                summary="Possible low-fiber pattern based on your recent meals. More vegetables, legumes, or whole grains may help.",
                actions=["Look for higher-fiber options such as vegetables, beans, or whole grains.", "Add fruit or greens to one meal today."],
            )
        )

    daily_totals = defaultdict(NutritionTotals)
    for record in window_records:
        bucket = daily_totals[record.captured_at.date().isoformat()]
        nutrition = record.meal_state.nutrition
        bucket.calories += float(nutrition.calories)
        bucket.sugar_g += float(nutrition.sugar_g)
        bucket.sodium_mg += float(nutrition.sodium_mg)

    avg_daily_sodium = sum(bucket.sodium_mg for bucket in daily_totals.values()) / len(daily_totals)
    sodium_heavy_meals = sum(1 for record in window_records if record.meal_state.nutrition.sodium_mg > 900.0)
    if avg_daily_sodium > float(profile.daily_sodium_limit_mg) * 0.9 or sodium_heavy_meals >= 3:
        insights.append(
            NutritionInsight(
                code="high_sodium_pattern",
                title="Sodium exposure looks elevated",
                summary="Possible high-sodium pattern based on your recent meals. Lower-sodium choices may better match your target.",
                actions=["Prefer soups or sauces with less gravy.", "Swap one salty dish for a lower-sodium option today."],
            )
        )

    avg_daily_sugar = sum(bucket.sugar_g for bucket in daily_totals.values()) / len(daily_totals)
    sugar_heavy_meals = sum(1 for record in window_records if record.meal_state.nutrition.sugar_g > 15.0)
    if avg_daily_sugar > float(profile.daily_sugar_limit_g) * 0.9 or sugar_heavy_meals >= 3:
        insights.append(
            NutritionInsight(
                code="high_sugar_pattern",
                title="Sugar intake may be trending high",
                summary="Possible higher-sugar pattern based on your recent meals. A few lower-sugar swaps could help steady your intake.",
                actions=["Choose drinks and sauces with less added sugar.", "Favor lower-sugar meals for your next meal slot."],
            )
        )

    calorie_target = float(profile.target_calories_per_day or 0.0)
    if calorie_target > 0:
        avg_daily_calories = sum(bucket.calories for bucket in daily_totals.values()) / len(daily_totals)
        if avg_daily_calories > calorie_target * 1.1:
            insights.append(
                NutritionInsight(
                    code="high_calorie_pattern",
                    title="Calories are running ahead of target",
                    summary="Possible higher-calorie pattern based on your recent meals. Lighter portions may improve your daily pacing.",
                    actions=["Use a smaller portion size for one meal today.", "Balance rich meals with a lighter next meal."],
                )
            )

    repeats = Counter(_normalize_dish_name(record.meal_state.dish_name) for record in window_records)
    if any(count >= 3 for count in repeats.values()):
        insights.append(
            NutritionInsight(
                code="repetitive_meal_pattern",
                title="Recent meals are quite repetitive",
                summary="Possible repetitive meal pattern based on your recent logs. A bit more variety may improve nutrient balance.",
                actions=["Try one new protein or vegetable source this week.", "Rotate between two or three meal types instead of repeating one dish."],
            )
        )

    return insights


def _recommendation_hints(insights: list[NutritionInsight]) -> list[str]:
    hints: list[str] = []
    for code in [item.code for item in insights]:
        if code == "low_protein_pattern" and "higher_protein" not in hints:
            hints.append("higher_protein")
        if code == "low_fiber_pattern" and "higher_fiber" not in hints:
            hints.append("higher_fiber")
        if code == "high_sodium_pattern" and "lower_sodium" not in hints:
            hints.append("lower_sodium")
        if code == "high_sugar_pattern" and "lower_sugar" not in hints:
            hints.append("lower_sugar")
    return hints
