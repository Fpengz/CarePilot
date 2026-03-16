"""Tests for meal context ingestion helpers."""

from care_pilot.features.meals.use_cases.context import build_context_snapshot


def test_build_context_snapshot_includes_request_and_device_metadata() -> None:
    snapshot = build_context_snapshot(
        session={"profile_mode": "member", "display_name": "Auntie Mei"},
        request_id="req-123",
        correlation_id="corr-456",
        user_agent="Mozilla/5.0",
        client_ip="127.0.0.1",
    )

    assert snapshot.request_id == "req-123"
    assert snapshot.correlation_id == "corr-456"
    assert snapshot.user_agent == "Mozilla/5.0"
    assert snapshot.client_ip == "127.0.0.1"
    assert snapshot.user_context_snapshot["profile_mode"] == "member"
    assert snapshot.user_context_snapshot["display_name"] == "Auntie Mei"
