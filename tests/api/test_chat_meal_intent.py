"""Tests for chat meal logging intent detection."""

from __future__ import annotations

from care_pilot.features.companion.chat.meal_intent import (
    MealLogIntentResult,
    detect_meal_log_intent,
)


def test_detect_meal_log_intent_from_natural_language() -> None:
    result = detect_meal_log_intent("I ate chicken rice for lunch.")

    assert result.intent is True
    assert result.meal_text == "chicken rice"


def test_detect_meal_log_intent_ignores_questions() -> None:
    result = detect_meal_log_intent("Can I eat chicken rice?")

    assert result.intent is False


def test_detect_meal_log_intent_respects_explicit_command() -> None:
    result = detect_meal_log_intent("[MEAL] fish soup")

    assert result.intent is True
    assert result.meal_text == "fish soup"


def test_detect_meal_log_intent_uses_classifier_when_uncertain() -> None:
    called = {"value": False}

    def _classifier(_: str) -> MealLogIntentResult:
        called["value"] = True
        return MealLogIntentResult(
            intent=True,
            meal_text="toasted sandwich",
            confidence=0.72,
            reason="llm_fallback",
            source="llm",
        )

    result = detect_meal_log_intent("Lunch was solid", classifier=_classifier)

    assert called["value"] is True
    assert result.intent is True
