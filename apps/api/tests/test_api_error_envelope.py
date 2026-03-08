from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _force_in_memory_auth_backend(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "in_memory")
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def test_unauthorized_response_uses_standard_error_envelope() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    body = response.json()
    assert body["detail"] == "authentication required"
    assert body["error"]["code"] == "auth.unauthorized"
    assert body["error"]["message"] == "authentication required"
    assert body["error"]["status_code"] == 401
    assert isinstance(body["error"]["details"], dict)
    assert body["error"]["correlation_id"]


def test_validation_error_response_uses_standard_error_envelope() -> None:
    client = TestClient(create_app())

    response = client.post("/api/v1/auth/signup", json={"email": "member@example.com"})

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "request validation failed"
    assert body["error"]["code"] == "request.validation_error"
    assert body["error"]["message"] == "request validation failed"
    assert body["error"]["status_code"] == 422
    assert "errors" in body["error"]["details"]
    assert body["error"]["correlation_id"]
