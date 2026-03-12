"""
Format companion case snapshots for chat context.

This module converts case snapshot data into a compact textual context
block that can be injected into chat prompts.
"""

from __future__ import annotations

from typing import Iterable, Protocol

from dietary_guardian.features.companion.core.domain import CaseSnapshot
from dietary_guardian.features.companion.core.health.models import HealthProfileRecord
from dietary_guardian.features.meals.domain import meal_display_name, meal_nutrition
from dietary_guardian.features.meals.domain.recognition import MealRecognitionRecord
from dietary_guardian.platform.observability.workflows.domain.models import WorkflowTimelineEvent


def _join_or_none(values: Iterable[str]) -> str:
    items = [value for value in values if value]
    return ", ".join(items) if items else "none"


class ToolSummary(Protocol):
    """Minimal tool summary contract for chat context."""

    name: str
    purpose: str


def format_chat_context(
    *,
    snapshot: CaseSnapshot,
    recent_meals: list[MealRecognitionRecord],
    health_profile: HealthProfileRecord | None = None,
    tool_specs: Iterable[ToolSummary] | None = None,
    recent_events: Iterable[WorkflowTimelineEvent] | None = None,
    max_meals: int = 5,
    max_biomarkers: int = 6,
    max_events: int = 4,
) -> str:
    lines: list[str] = [
        f"Profile: {snapshot.profile_name}",
        f"Conditions: {_join_or_none(snapshot.conditions)}",
        f"Medications: {_join_or_none(snapshot.medications)}",
        f"Latest meal: {snapshot.latest_meal_name or 'none'}",
        f"Meal count: {snapshot.meal_count}",
        f"Meal risk streak: {snapshot.meal_risk_streak}",
        f"Reminder response rate: {snapshot.reminder_response_rate:.2f}",
    ]
    if snapshot.adherence_rate is not None:
        lines.append(f"Medication adherence rate: {snapshot.adherence_rate:.2f}")
    if snapshot.symptom_count:
        lines.append(f"Symptoms logged: {snapshot.symptom_count} (avg severity {snapshot.average_symptom_severity:.1f})")
    if snapshot.active_risk_flags:
        lines.append(f"Active risk flags: {', '.join(snapshot.active_risk_flags)}")

    if snapshot.biomarker_summary:
        biomarker_items = list(snapshot.biomarker_summary.items())[:max_biomarkers]
        biomarker_text = ", ".join(f"{key}={value}" for key, value in biomarker_items)
        lines.append(f"Biomarkers: {biomarker_text}")

    if health_profile is not None:
        if health_profile.age is not None:
            lines.append(f"Age: {health_profile.age}")
        if health_profile.conditions:
            condition_names = [getattr(item, "name", str(item)) for item in health_profile.conditions]
            lines.append(f"Profile conditions: {_join_or_none(condition_names)}")
        if health_profile.medications:
            medication_names = [getattr(item, "name", str(item)) for item in health_profile.medications]
            lines.append(f"Profile medications: {_join_or_none(medication_names)}")
        if health_profile.allergies:
            lines.append(f"Allergies: {_join_or_none(health_profile.allergies)}")
        if health_profile.nutrition_goals:
            lines.append(f"Nutrition goals: {_join_or_none(health_profile.nutrition_goals)}")
        if health_profile.preferred_cuisines:
            lines.append(f"Preferred cuisines: {_join_or_none(health_profile.preferred_cuisines)}")
        if health_profile.disliked_ingredients:
            lines.append(f"Disliked ingredients: {_join_or_none(health_profile.disliked_ingredients)}")
        if health_profile.macro_focus:
            lines.append(f"Macro focus: {_join_or_none(health_profile.macro_focus)}")
        lines.append(f"Daily sodium limit: {int(health_profile.daily_sodium_limit_mg)} mg")
        lines.append(f"Daily sugar limit: {int(health_profile.daily_sugar_limit_g)} g")
        lines.append(f"Daily protein target: {int(health_profile.daily_protein_target_g)} g")
        lines.append(f"Daily fiber target: {int(health_profile.daily_fiber_target_g)} g")
        if health_profile.target_calories_per_day:
            lines.append(f"Target calories: {int(health_profile.target_calories_per_day)} kcal")
        lines.append(f"Budget tier: {health_profile.budget_tier}")

    meal_lines: list[str] = []
    for record in recent_meals[-max_meals:]:
        nutrition = meal_nutrition(record)
        meal_lines.append(f"- {meal_display_name(record)} ({round(nutrition.calories)} kcal)")
    if meal_lines:
        lines.append("Recent meals:")
        lines.extend(meal_lines)

    event_items = list(recent_events or [])
    if event_items:
        lines.append("Recent activity:")
        for event in event_items[-max_events:]:
            workflow_name = f"{event.workflow_name} " if event.workflow_name else ""
            lines.append(f"- {workflow_name}{event.event_type}".strip())

    tool_items = [spec for spec in tool_specs or [] if getattr(spec, "name", None)]
    if tool_items:
        lines.append("Available tools:")
        for spec in tool_items:
            purpose = getattr(spec, "purpose", "")
            if purpose:
                lines.append(f"- {spec.name}: {purpose}")
            else:
                lines.append(f"- {spec.name}")

    return "\n".join(lines)
