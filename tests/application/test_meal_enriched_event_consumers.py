"""Tests for meal enriched event consumers."""

from datetime import date, datetime, timezone
from typing import Any, cast

from dietary_guardian.application.companion.snapshot import build_case_snapshot
from dietary_guardian.domain.health.models import ClinicalProfileSnapshot, HealthProfileRecord
from dietary_guardian.domain.identity.models import (
    MedicalCondition,
    Medication,
    UserProfile,
)
from dietary_guardian.domain.meals import (
    EnrichedMealEvent,
    MealNutritionProfile,
    MealPortionEstimate,
    NormalizedMealItem,
)
from dietary_guardian.domain.recommendations.models import (
    CanonicalFoodRecord,
    PreferenceSnapshot,
    RecommendationInteraction,
)
from dietary_guardian.domain.meals.models import Ingredient, MealState, Nutrition
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord
from dietary_guardian.domain.meals import build_daily_nutrition_summary
from dietary_guardian.domain.metrics import meal_calorie_points
from dietary_guardian.domain.recommendations.engine import (
    _snapshot_from_history,
    build_substitution_plan,
    build_temporal_context,
)
from dietary_guardian.domain.recommendations.meal_recommendations import generate_recommendation
from dietary_guardian.domain.meals import build_weekly_nutrition_summary


def _record(*, enriched: bool = True) -> MealRecognitionRecord:
    meal_state = MealState(
        dish_name="Unknown dish",
        confidence_score=0.55,
        identification_method="AI_Flash",
        ingredients=[Ingredient(name="fallback ingredient")],
        nutrition=Nutrition(calories=100, carbs_g=10, sugar_g=1, protein_g=2, fat_g=3, sodium_mg=120),
    )
    enriched_event = None
    if enriched:
        enriched_event = EnrichedMealEvent(
            meal_name="Chicken Rice Set",
            normalized_items=[
                NormalizedMealItem(
                    detected_label="chicken rice",
                    canonical_food_id="sg-chicken-rice",
                    canonical_name="Chicken Rice",
                    match_strategy="exact_alias",
                    match_confidence=0.96,
                    portion_estimate=MealPortionEstimate(amount=1, unit="plate", confidence=0.8),
                    estimated_grams=320.0,
                    nutrition=MealNutritionProfile(
                        calories=640,
                        carbs_g=72,
                        sugar_g=4,
                        protein_g=28,
                        fat_g=20,
                        sodium_mg=980,
                        fiber_g=3,
                    ),
                    risk_tags=["high_sodium"],
                )
            ],
            total_nutrition=MealNutritionProfile(
                calories=640,
                carbs_g=72,
                sugar_g=4,
                protein_g=28,
                fat_g=20,
                sodium_mg=980,
                fiber_g=3,
            ),
            risk_tags=["high_sodium"],
        )
    return MealRecognitionRecord(
        id="meal-1",
        user_id="u1",
        captured_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        source="upload",
        meal_state=meal_state,
        enriched_event=enriched_event,
    )


def _profile() -> HealthProfileRecord:
    return HealthProfileRecord(
        user_id="u1",
        target_calories_per_day=1800,
        daily_sodium_limit_mg=2000,
        daily_sugar_limit_g=30,
        daily_protein_target_g=60,
        daily_fiber_target_g=25,
    )


def _user() -> UserProfile:
    return UserProfile(
        id="u1",
        name="Mr Tan",
        age=68,
        conditions=[MedicalCondition(name="Hypertension", severity="High")],
        medications=[Medication(name="Amlodipine", dosage="5mg")],
    )


class _FakeRecommendationRepo:
    def __init__(self, source: CanonicalFoodRecord, alternative: CanonicalFoodRecord, meal_record: MealRecognitionRecord) -> None:
        self._source = source
        self._alternative = alternative
        self._meal_record = meal_record
        self._snapshot: PreferenceSnapshot | None = None

    def list_canonical_foods(self, *, locale: str, slot: str | None = None, limit: int = 100) -> list[CanonicalFoodRecord]:
        items = [self._source, self._alternative]
        if slot is not None:
            items = [item for item in items if item.slot == slot]
        return items[:limit]

    def get_preference_snapshot(self, user_id: str) -> PreferenceSnapshot | None:
        return self._snapshot

    def save_preference_snapshot(self, snapshot: PreferenceSnapshot) -> PreferenceSnapshot:
        self._snapshot = snapshot
        return snapshot

    def get_meal_record(self, user_id: str, meal_id: str) -> MealRecognitionRecord | None:
        if self._meal_record.id == meal_id and self._meal_record.user_id == user_id:
            return self._meal_record
        return None

    def get_canonical_food(self, food_id: str) -> CanonicalFoodRecord | None:
        for item in [self._source, self._alternative]:
            if item.food_id == food_id:
                return item
        return None

    def find_food_by_name(self, *, locale: str, name: str) -> CanonicalFoodRecord | None:
        for item in [self._source, self._alternative]:
            if item.title == name:
                return item
        return None

    def save_recommendation_interaction(self, interaction: RecommendationInteraction) -> RecommendationInteraction:
        return interaction


class _LocaleAwareRecommendationRepo(_FakeRecommendationRepo):
    def __init__(self, source: CanonicalFoodRecord, alternative: CanonicalFoodRecord, meal_record: MealRecognitionRecord) -> None:
        super().__init__(source=source, alternative=alternative, meal_record=meal_record)
        self.seen_locales: list[str] = []

    def find_food_by_name(self, *, locale: str, name: str) -> CanonicalFoodRecord | None:
        self.seen_locales.append(locale)
        return super().find_food_by_name(locale=locale, name=name)


def _canonical_food(*, food_id: str, title: str, calories: float, sodium_mg: float, sugar_g: float) -> CanonicalFoodRecord:
    return CanonicalFoodRecord(
        food_id=food_id,
        title=title,
        slot="lunch",
        venue_type="hawker",
        cuisine_tags=["local"],
        ingredient_tags=["rice", "chicken"],
        preparation_tags=["savory"],
        nutrition=Nutrition(
            calories=calories,
            carbs_g=60,
            sugar_g=sugar_g,
            protein_g=25,
            fat_g=18,
            sodium_mg=sodium_mg,
            fiber_g=2,
        ),
        health_tags=["lower_sodium"] if sodium_mg < 980 else [],
    )


def test_daily_summary_prefers_enriched_nutrition() -> None:
    summary = build_daily_nutrition_summary(
        profile=_profile(),
        meal_history=[_record()],
        summary_date=date(2026, 3, 1),
    )

    assert summary.consumed.calories == 640
    assert summary.consumed.sodium_mg == 980


def test_weekly_summary_prefers_enriched_display_name() -> None:
    summary = cast(dict[str, Any], build_weekly_nutrition_summary(
        meal_history=[_record(), _record()],
        week_start=date(2026, 2, 23),
    ))

    totals = cast(dict[str, float], summary["totals"])
    pattern_flags = cast(list[str], summary["pattern_flags"])
    assert totals["calories"] == 1280.0
    assert "repetitive_meals" not in pattern_flags


def test_case_snapshot_uses_enriched_meal_context() -> None:
    snapshot = build_case_snapshot(
        user_profile=_user(),
        health_profile=_profile(),
        meals=[_record()],
        reminders=[],
        adherence_events=[],
        symptoms=[],
        biomarker_readings=[],
        clinical_snapshot=ClinicalProfileSnapshot(biomarkers={"ldl": 3.8}),
    )

    assert snapshot.latest_meal_name == "Chicken Rice Set"
    assert snapshot.meal_risk_streak == 1


def test_metrics_and_recommendation_use_enriched_event() -> None:
    record = _record()

    points = meal_calorie_points([record])
    recommendation = generate_recommendation(record, ClinicalProfileSnapshot(biomarkers={}), _user())

    assert points[0].value == 640
    assert "Chicken Rice Set" in recommendation.rationale


def test_recommendation_agent_uses_enriched_titles_for_temporal_and_substitution_flows() -> None:
    record = _record()
    source = _canonical_food(food_id="source", title="Chicken Rice Set", calories=640, sodium_mg=980, sugar_g=4)
    alternative = _canonical_food(food_id="alt", title="Fish Soup", calories=420, sodium_mg=480, sugar_g=2)
    repo = _FakeRecommendationRepo(source=source, alternative=alternative, meal_record=record)

    temporal = build_temporal_context(meal_history=[record], interaction_count=0)
    plan = build_substitution_plan(
        repository=repo,
        user_id="u1",
        health_profile=_profile(),
        user_profile=_user(),
        meal_history=[record],
        clinical_snapshot=None,
        source_meal_id=record.id,
        limit=1,
    )

    assert temporal.recent_repeat_titles == ["Chicken Rice Set"]
    assert plan is not None
    assert plan.source_meal.title == "Chicken Rice Set"
    assert [item.title for item in plan.alternatives] == ["Fish Soup"]


def test_snapshot_bootstrap_uses_catalog_locale_for_exact_meal_lookup() -> None:
    record = _record()
    source = _canonical_food(food_id="source", title="Chicken Rice Set", calories=640, sodium_mg=980, sugar_g=4)
    source.locale = "zh-SG"
    alternative = _canonical_food(food_id="alt", title="Fish Soup", calories=420, sodium_mg=480, sugar_g=2)
    alternative.locale = "zh-SG"
    repo = _LocaleAwareRecommendationRepo(source=source, alternative=alternative, meal_record=record)

    snapshot = _snapshot_from_history(
        repository=repo,
        user_id="u1",
        meal_history=[record],
        catalog=[source, alternative],
    )

    assert repo.seen_locales == ["zh-SG"]
    assert snapshot.ingredient_affinity.get("rice", 0.0) > 0.0
