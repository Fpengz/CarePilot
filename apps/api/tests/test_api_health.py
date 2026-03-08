from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _isolated_health_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("LLM_PROVIDER", "test")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("EPHEMERAL_STATE_BACKEND", "in_memory")
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def test_health_endpoints() -> None:
    client = TestClient(create_app())

    live = client.get("/api/v1/health/live")
    ready = client.get("/api/v1/health/ready")

    assert live.status_code == 200
    assert ready.status_code == 200
    ready_body = ready.json()
    assert ready_body["status"] in {"ready", "degraded", "not_ready"}
    assert ready_body["app_env"] == "dev"
    assert isinstance(ready_body["checks"], list)
    assert isinstance(ready_body["warnings"], list)
    assert isinstance(ready_body["errors"], list)
    assert "alerts_outbox_v2" in ready_body


def test_health_config_requires_authenticated_admin() -> None:
    client = TestClient(create_app())

    unauthenticated = client.get("/api/v1/health/config")
    assert unauthenticated.status_code == 401

    member_login = client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
    assert member_login.status_code == 200
    forbidden = client.get("/api/v1/health/config")
    assert forbidden.status_code == 403

    admin_client = TestClient(create_app())
    admin_login = admin_client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-pass"})
    assert admin_login.status_code == 200
    config = admin_client.get("/api/v1/health/config")
    assert config.status_code == 200
    assert "llm_provider" in config.json()


def test_health_ready_reports_degraded_when_optional_notification_config_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EMAIL_DEV_MODE", "0")
    monkeypatch.delenv("EMAIL_SMTP_HOST", raising=False)
    _reset_settings_cache()
    client = TestClient(create_app())

    ready = client.get("/api/v1/health/ready")

    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "degraded"
    assert any(check["name"] == "email_configuration" and check["status"] == "warn" for check in body["checks"])


def test_health_ready_reports_not_ready_when_required_redis_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EPHEMERAL_STATE_BACKEND", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6399/0")
    _reset_settings_cache()
    client = TestClient(create_app())

    ready = client.get("/api/v1/health/ready")

    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "not_ready"
    assert any(check["name"] == "redis_connectivity" and check["status"] == "fail" for check in body["checks"])


def test_request_context_headers_are_emitted_and_passthrough() -> None:
    client = TestClient(create_app())

    generated = client.get("/api/v1/health/live")
    assert generated.status_code == 200
    assert generated.headers.get("x-request-id")
    assert generated.headers.get("x-correlation-id")

    custom = client.get(
        "/api/v1/health/live",
        headers={
            "X-Request-ID": "req-custom-123",
            "X-Correlation-ID": "corr-custom-456",
        },
    )
    assert custom.status_code == 200
    assert custom.headers.get("x-request-id") == "req-custom-123"
    assert custom.headers.get("x-correlation-id") == "corr-custom-456"
