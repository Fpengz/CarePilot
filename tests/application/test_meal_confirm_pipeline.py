"""Tests for meal confirmation pipeline behavior."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from care_pilot.agent.dietary.schemas import DietaryAgentOutput
from care_pilot.config.app import get_settings
from care_pilot.features.meals.deps import MealDeps
from care_pilot.features.meals.domain.models import (
    CandidateMealEvent,
    MealCandidateRecord,
    MealNutritionProfile,
    MealPortionEstimate,
    NormalizedMealItem,
    NutritionRiskProfile,
    ValidatedMealEvent,
)
from care_pilot.features.meals.use_cases.confirm_meal import confirm_meal_candidate
from care_pilot.platform.cache import EventTimelineService


class _StubMealStore:
    def __init__(self, record: MealCandidateRecord) -> None:
        self._record = record
        self.saved_candidates: list[MealCandidateRecord] = []
        self.saved_events: list[ValidatedMealEvent] = []
        self.saved_profiles: list[NutritionRiskProfile] = []

    def get_meal_candidate(self, user_id: str, candidate_id: str) -> MealCandidateRecord | None:
        if self._record.user_id == user_id and self._record.candidate_id == candidate_id:
            return self._record
        return None

    def save_meal_candidate(self, record: MealCandidateRecord) -> None:
        self.saved_candidates.append(record)

    def save_validated_meal_event(self, event: ValidatedMealEvent) -> None:
        self.saved_events.append(event)

    def save_nutrition_risk_profile(self, profile: NutritionRiskProfile) -> None:
        self.saved_profiles.append(profile)


class _StubMemoryStore:
    def __init__(self) -> None:
        self.enabled = True
        self.calls: list[dict[str, object]] = []

    def search(self, *, user_id: str, query: str, limit: int) -> list[Any]:
        del user_id, query, limit
        return []

    def add_messages(
        self,
        *,
        user_id: str,
        session_id: str,
        messages: list[dict[str, str]],
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.calls.append(
            {
                "user_id": user_id,
                "session_id": session_id,
                "messages": messages,
                "metadata": metadata or {},
            }
        )


def _build_candidate_record() -> MealCandidateRecord:
    item = NormalizedMealItem(
        detected_label="Chicken",
        canonical_food_id="chicken",
        canonical_name="Chicken",
        match_strategy="exact_alias",
        match_confidence=0.9,
        portion_estimate=MealPortionEstimate(amount=1.0, unit="plate", confidence=0.8),
        nutrition=MealNutritionProfile(
            calories=500,
            carbs_g=40,
            sugar_g=2,
            protein_g=30,
            fat_g=15,
            sodium_mg=800,
            fiber_g=2,
        ),
        risk_tags=["high_sodium"],
        source_dataset="seed",
    )
    validated = ValidatedMealEvent(
        user_id="user-1",
        meal_name="Chicken",
        canonical_items=[item],
        alternatives=[],
        confidence_summary={},
        provenance={},
        needs_manual_review=False,
    )
    nutrition_profile = NutritionRiskProfile(
        event_id=validated.event_id,
        user_id=validated.user_id,
        captured_at=validated.captured_at,
        calories=500,
        carbs_g=40,
        sugar_g=2,
        protein_g=30,
        fat_g=15,
        sodium_mg=800,
        fiber_g=2,
        risk_tags=["high_sodium"],
        uncertainty={},
    )
    candidate_event = CandidateMealEvent(
        meal_name="Chicken",
        normalized_items=[item],
        total_nutrition=MealNutritionProfile(
            calories=500,
            carbs_g=40,
            sugar_g=2,
            protein_g=30,
            fat_g=15,
            sodium_mg=800,
            fiber_g=2,
        ),
        risk_tags=["high_sodium"],
        unresolved_items=[],
        source_records=[],
        needs_manual_review=False,
        summary="Chicken with 1 detected item(s)",
    )
    return MealCandidateRecord(
        user_id="user-1",
        candidate_event=candidate_event,
        validated_event=validated,
        nutrition_profile=nutrition_profile,
        request_id="req-1",
        correlation_id="corr-1",
        source="upload",
    )


@pytest.mark.asyncio
async def test_confirm_meal_runs_dietary_agent_and_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    record = _build_candidate_record()
    meal_store = _StubMealStore(record)
    memory_store = _StubMemoryStore()
    deps = MealDeps(
        settings=get_settings(),
        stores=cast(Any, SimpleNamespace(meals=meal_store)),
        event_timeline=EventTimelineService(),
        memory_store=memory_store,
    )
    called: dict[str, int] = {"dietary": 0}

    async def _fake_analyze(_input):  # noqa: ANN001
        called["dietary"] += 1
        return DietaryAgentOutput(
            analysis="ok",
            advice="stay balanced",
            is_safe=True,
            warnings=[],
        )

    monkeypatch.setattr(
        "care_pilot.features.meals.use_cases.confirm_meal.analyze_dietary_request",
        _fake_analyze,
    )

    updated = await confirm_meal_candidate(
        deps=deps,
        user_id="user-1",
        candidate_id=record.candidate_id,
        action="confirm",
        session_id="session-1",
        user_name="Auntie Mei",
    )

    assert updated.confirmation_status == "confirmed"
    assert called["dietary"] == 1
    assert memory_store.calls
    events = deps.event_timeline.get_events(correlation_id="corr-1")
    event_types = {event.event_type for event in events}
    assert "dietary_agent_executed" in event_types
    assert "memory_snippet_written" in event_types


@pytest.mark.asyncio
async def test_skip_meal_skips_dietary_agent_and_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    record = _build_candidate_record()
    meal_store = _StubMealStore(record)
    memory_store = _StubMemoryStore()
    deps = MealDeps(
        settings=get_settings(),
        stores=cast(Any, SimpleNamespace(meals=meal_store)),
        event_timeline=EventTimelineService(),
        memory_store=memory_store,
    )
    called: dict[str, int] = {"dietary": 0}

    async def _fake_analyze(_input):  # noqa: ANN001
        called["dietary"] += 1
        return DietaryAgentOutput(
            analysis="ok",
            advice="stay balanced",
            is_safe=True,
            warnings=[],
        )

    monkeypatch.setattr(
        "care_pilot.features.meals.use_cases.confirm_meal.analyze_dietary_request",
        _fake_analyze,
    )

    updated = await confirm_meal_candidate(
        deps=deps,
        user_id="user-1",
        candidate_id=record.candidate_id,
        action="skip",
        session_id="session-1",
        user_name="Auntie Mei",
    )

    assert updated.confirmation_status == "skipped"
    assert called["dietary"] == 0
    assert memory_store.calls == []
    events = deps.event_timeline.get_events(correlation_id="corr-1")
    event_types = {event.event_type for event in events}
    assert "dietary_agent_executed" not in event_types
    assert "memory_snippet_written" not in event_types
