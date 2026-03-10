"""Module for test api observability contract."""

import logging
from collections.abc import Generator
from io import BytesIO

import pytest
from apps.api.dietary_api.main import create_app
from fastapi.testclient import TestClient
from PIL import Image

from dietary_guardian.config.app import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_observability_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _jpeg_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), color=(255, 0, 0))
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_header_propagation_contract_on_api_routes(sqlite_observability_env: None) -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    response = client.get(
        "/api/v1/meal/records",
        headers={"X-Request-ID": "req-contract-1", "X-Correlation-ID": "corr-contract-1"},
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-contract-1"
    assert response.headers["x-correlation-id"] == "corr-contract-1"


def test_invalid_trace_headers_are_normalized(sqlite_observability_env: None) -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    response = client.get(
        "/api/v1/meal/records",
        headers={"X-Request-ID": "   ", "X-Correlation-ID": "    "},
    )
    assert response.status_code == 200
    request_id = response.headers["x-request-id"]
    correlation_id = response.headers["x-correlation-id"]
    assert request_id.strip()
    assert correlation_id.strip()
    assert request_id != "   "
    assert correlation_id != "    "


def test_request_logs_include_standardized_outcome_and_latency(
    sqlite_observability_env: None, caplog: pytest.LogCaptureFixture
) -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    caplog.set_level(logging.INFO)
    response = client.get(
        "/api/v1/meal/records",
        headers={"X-Request-ID": "req-observe-1", "X-Correlation-ID": "corr-observe-1"},
    )
    assert response.status_code == 200
    request_logs = [record.message for record in caplog.records if "event=api_request_complete" in record.message]
    assert request_logs
    message = request_logs[-1]
    assert "outcome=success" in message
    assert "latency_ms=" in message
    assert "request_id=req-observe-1" in message
    assert "correlation_id=corr-observe-1" in message


def test_meal_workflow_uses_incoming_correlation_contract(sqlite_observability_env: None) -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    response = client.post(
        "/api/v1/meal/analyze",
        headers={"X-Request-ID": "req-meal-contract", "X-Correlation-ID": "corr-meal-contract"},
        files={"file": ("meal.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["workflow"]["request_id"] == "req-meal-contract"
    assert body["workflow"]["correlation_id"] == "corr-meal-contract"
    timeline = body["workflow"]["timeline_events"]
    assert timeline
    assert all(event["request_id"] == "req-meal-contract" for event in timeline)
    assert all(event["correlation_id"] == "corr-meal-contract" for event in timeline)


def test_alert_workflow_uses_incoming_correlation_contract(sqlite_observability_env: None) -> None:
    client = TestClient(create_app())
    _login(client, "admin@example.com", "admin-pass")
    response = client.post(
        "/api/v1/alerts/trigger",
        headers={"X-Request-ID": "req-alert-contract", "X-Correlation-ID": "corr-alert-contract"},
        json={
            "alert_type": "manual_test_alert",
            "severity": "warning",
            "message": "Observability propagation contract",
            "destinations": ["in_app"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["workflow"]["request_id"] == "req-alert-contract"
    assert body["workflow"]["correlation_id"] == "corr-alert-contract"
    timeline = body["workflow"]["timeline_events"]
    assert timeline
    assert all(event["request_id"] == "req-alert-contract" for event in timeline)
    assert all(event["correlation_id"] == "corr-alert-contract" for event in timeline)


def test_failure_logs_include_enriched_metadata(
    sqlite_observability_env: None, caplog: pytest.LogCaptureFixture
) -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    caplog.set_level(logging.WARNING)
    response = client.post(
        "/api/v1/suggestions/generate-from-report",
        headers={"X-Request-ID": "req-failure-log", "X-Correlation-ID": "corr-failure-log"},
        json={"text": "HbA1c 7.3 LDL 4.1"},
    )
    assert response.status_code == 400
    failures = [record.message for record in caplog.records if "event=api_request_failed" in record.message]
    assert failures
    message = failures[-1]
    assert "request_id=req-failure-log" in message
    assert "correlation_id=corr-failure-log" in message
    assert "error_code=suggestions.no_meal_records" in message
    assert "failure_metadata" in message
