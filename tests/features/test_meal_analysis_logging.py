"""Tests for meal analysis logging payloads."""

import logging

from care_pilot.config.llm import (
    LLMCapability,
    LLMCapabilityTarget,
    LLMSettings,
    ModelProvider,
)
from care_pilot.features.meals.logging import (
    build_meal_analysis_log_payload,
    log_meal_analysis_event,
    resolve_meal_analysis_model_name,
)


def test_build_meal_analysis_log_payload_includes_core_fields() -> None:
    payload = build_meal_analysis_log_payload(
        user_id="user-1",
        request_id="req-1",
        correlation_id="corr-1",
        provider="gemini",
        model_name="model-x",
        meal_id="meal-123",
        meal_name="Chicken Rice",
        manual_review=True,
        latency_ms=1234.5,
        unresolved_count=2,
        risk_tags=["high_sodium"],
    )

    assert payload["user_id"] == "user-1"
    assert payload["request_id"] == "req-1"
    assert payload["correlation_id"] == "corr-1"
    assert payload["provider"] == "gemini"
    assert payload["model_name"] == "model-x"
    assert payload["meal_id"] == "meal-123"
    assert payload["meal_name"] == "Chicken Rice"
    assert payload["manual_review"] is True
    assert payload["latency_ms"] == 1234.5
    assert payload["unresolved_count"] == 2
    assert payload["risk_tag_count"] == 1


def test_resolve_meal_analysis_model_prefers_capability_target() -> None:
    settings = LLMSettings(
        provider=ModelProvider.TEST,
        capability_map={
            LLMCapability.MEAL_VISION: LLMCapabilityTarget(
                provider=ModelProvider.OPENAI, model="vision-x"
            ),
        },
    )

    assert (
        resolve_meal_analysis_model_name(settings, provider="gemini")
        == "vision-x"
    )


def test_log_meal_analysis_event_emits_payload(caplog) -> None:
    caplog.set_level(logging.INFO)
    payload = build_meal_analysis_log_payload(
        user_id="user-1",
        request_id="req-1",
        correlation_id="corr-1",
        provider="gemini",
        model_name="model-x",
        meal_id="meal-123",
        meal_name="Chicken Rice",
        manual_review=False,
        latency_ms=456.0,
        unresolved_count=0,
        risk_tags=[],
    )

    log_meal_analysis_event(payload)

    assert "meal_analysis_completed" in caplog.text
    assert "user_id=user-1" in caplog.text
