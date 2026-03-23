"""Tests for chat context formatting."""

from dataclasses import dataclass

from care_pilot.features.companion.core.chat_context import format_chat_context
from care_pilot.features.companion.core.domain import CaseSnapshot
from care_pilot.features.companion.core.health.models import HealthProfileRecord
from care_pilot.features.meals.domain.models import Ingredient, MealState, Nutrition, PortionSize
from care_pilot.features.meals.domain.recognition import MealRecognitionRecord
from care_pilot.features.profiles.domain.models import MedicalCondition, Medication
from care_pilot.platform.observability.workflows.domain.models import WorkflowTimelineEvent


def test_format_chat_context_includes_profile_and_meals() -> None:
    snapshot = CaseSnapshot(
        user_id="u1",
        profile_name="Alex",
        conditions=["hypertension"],
        medications=["amlodipine"],
        meal_count=2,
        latest_meal_name="Chicken Rice",
        meal_risk_streak=1,
        reminder_count=3,
        reminder_response_rate=0.5,
        adherence_events=2,
        adherence_rate=0.75,
        symptom_count=1,
        average_symptom_severity=2.0,
        biomarker_summary={"ldl": 3.2},
        active_risk_flags=["high_sodium"],
    )

    meal_state = MealState(
        dish_name="Chicken Rice",
        confidence_score=0.8,
        identification_method="AI_Flash",
        ingredients=[Ingredient(name="chicken"), Ingredient(name="rice")],
        nutrition=Nutrition(
            calories=620,
            carbs_g=80,
            sugar_g=4,
            protein_g=25,
            fat_g=20,
            sodium_mg=900,
        ),
        portion_size=PortionSize.STANDARD,
    )
    meals = [
        MealRecognitionRecord(id="m1", user_id="u1", source="chat", meal_state=meal_state),
    ]

    context = format_chat_context(snapshot=snapshot, recent_meals=meals)

    assert "Profile: Alex" in context
    assert "Conditions: hypertension" in context
    assert "Latest meal: Chicken Rice" in context
    assert "Recent meals:" in context
    assert "Chicken Rice" in context


def test_format_chat_context_includes_tool_summary() -> None:
    @dataclass
    class _ToolSummary:
        name: str
        purpose: str

    snapshot = CaseSnapshot(
        user_id="u1",
        profile_name="Alex",
        conditions=[],
        medications=[],
        meal_count=0,
        latest_meal_name=None,
        meal_risk_streak=0,
        reminder_count=0,
        reminder_response_rate=0.0,
        adherence_events=0,
        adherence_rate=None,
        symptom_count=0,
        average_symptom_severity=0.0,
        biomarker_summary={},
        active_risk_flags=[],
    )
    tool = _ToolSummary(name="trigger_alert", purpose="Send a safety alert")

    context = format_chat_context(snapshot=snapshot, recent_meals=[], tool_specs=[tool])

    assert "Available tools:" in context
    assert "trigger_alert" in context


def test_format_chat_context_includes_recent_activity() -> None:
    snapshot = CaseSnapshot(
        user_id="u1",
        profile_name="Alex",
        conditions=[],
        medications=[],
        meal_count=0,
        latest_meal_name=None,
        meal_risk_streak=0,
        reminder_count=0,
        reminder_response_rate=0.0,
        adherence_events=0,
        adherence_rate=None,
        symptom_count=0,
        average_symptom_severity=0.0,
        biomarker_summary={},
        active_risk_flags=[],
    )
    events = [
        WorkflowTimelineEvent(
            event_id="evt-1",
            event_type="workflow_completed",
            workflow_name="meal_analysis",
            request_id="req-1",
            correlation_id="corr-1",
            user_id="u1",
            payload={"dish_name": "Chicken Rice"},
        ),
    ]

    context = format_chat_context(snapshot=snapshot, recent_meals=[], recent_events=events)

    assert "Recent activity:" in context
    assert "meal_analysis" in context


def test_format_chat_context_includes_health_profile_details() -> None:
    snapshot = CaseSnapshot(
        user_id="u1",
        profile_name="Alex",
        conditions=["hypertension"],
        medications=["amlodipine"],
        meal_count=0,
        latest_meal_name=None,
        meal_risk_streak=0,
        reminder_count=0,
        reminder_response_rate=0.0,
        adherence_events=0,
        adherence_rate=None,
        symptom_count=0,
        average_symptom_severity=0.0,
        biomarker_summary={},
        active_risk_flags=[],
    )
    profile = HealthProfileRecord(
        user_id="u1",
        age=67,
        conditions=[MedicalCondition(name="hypertension", severity="High")],
        medications=[Medication(name="amlodipine", dosage="5mg")],
        allergies=["peanuts"],
        nutrition_goals=["low sodium"],
        preferred_cuisines=["local"],
        disliked_ingredients=["offal"],
        macro_focus=["protein"],
        daily_sodium_limit_mg=1800,
        daily_sugar_limit_g=25,
        daily_protein_target_g=70,
        daily_fiber_target_g=28,
        target_calories_per_day=1800,
        budget_tier="budget",
    )

    context = format_chat_context(snapshot=snapshot, recent_meals=[], health_profile=profile)

    assert "Age: 67" in context
    assert "Allergies: peanuts" in context
    assert "Nutrition goals: low sodium" in context
    assert "Preferred cuisines: local" in context
    assert "Disliked ingredients: offal" in context
