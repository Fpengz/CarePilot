"""
Format companion case snapshots for chat context.

This module converts case snapshot data into a compact textual context
block that can be injected into chat prompts.
"""

from __future__ import annotations

from typing import Iterable

from dietary_guardian.features.companion.core.domain import CaseSnapshot
from dietary_guardian.features.meals.domain import meal_display_name, meal_nutrition
from dietary_guardian.features.meals.domain.recognition import MealRecognitionRecord


def _join_or_none(values: Iterable[str]) -> str:
    items = [value for value in values if value]
    return ", ".join(items) if items else "none"


def format_chat_context(
    *,
    snapshot: CaseSnapshot,
    recent_meals: list[MealRecognitionRecord],
    max_meals: int = 5,
    max_biomarkers: int = 6,
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

    meal_lines: list[str] = []
    for record in recent_meals[-max_meals:]:
        nutrition = meal_nutrition(record)
        meal_lines.append(f"- {meal_display_name(record)} ({round(nutrition.calories)} kcal)")
    if meal_lines:
        lines.append("Recent meals:")
        lines.extend(meal_lines)

    return "\n".join(lines)
