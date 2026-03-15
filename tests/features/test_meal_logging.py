"""Tests for meal analysis logging payloads."""

from __future__ import annotations

from care_pilot.features.meals.logging import build_meal_analysis_log_payload


def test_meal_analysis_log_payload_includes_observation_and_inference_latency() -> None:
    payload = build_meal_analysis_log_payload(
        user_id="user-1",
        request_id="req-1",
        correlation_id="corr-1",
        provider="gemini",
        model_name="gemini-2.0",
        meal_id="event-123",
        meal_name="Laksa",
        manual_review=False,
        latency_ms=1234.0,
        inference_latency_ms=456.0,
        observation_id="obs-999",
        unresolved_count=1,
        risk_tags=["high_sodium"],
    )

    assert payload["observation_id"] == "obs-999"
    assert payload["meal_id"] == "event-123"
    assert payload["inference_latency_ms"] == 456.0
