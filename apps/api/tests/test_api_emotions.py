from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _emotion_enabled_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "in_memory")
    monkeypatch.setenv("EMOTION_INFERENCE_ENABLED", "true")
    monkeypatch.setenv("EMOTION_SPEECH_ENABLED", "true")
    monkeypatch.setenv("EMOTION_COMPAT_ROUTES_ENABLED", "true")
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.com", "password": "member-pass"},
    )
    assert response.status_code == 200


def test_emotions_text_requires_auth() -> None:
    client = TestClient(create_app())

    response = client.post("/api/v1/emotions/text", json={"text": "I feel good"})

    assert response.status_code == 401


def test_emotions_text_returns_observation() -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post(
        "/api/v1/emotions/text",
        json={"text": "I am really happy and calm after lunch."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["observation"]["source_type"] == "text"
    assert body["observation"]["emotion"] in {"happy", "neutral"}
    assert body["observation"]["confidence_band"] in {"high", "medium", "low"}
    assert isinstance(body["observation"]["evidence"], list)


def test_emotions_speech_returns_observation() -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post(
        "/api/v1/emotions/speech",
        files={"file": ("sample.wav", b"fake-wave-data", "audio/wav")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["observation"]["source_type"] == "speech"
    assert body["observation"]["emotion"] in {
        "happy",
        "sad",
        "angry",
        "frustrated",
        "anxious",
        "neutral",
        "confused",
        "fearful",
    }


def test_emotions_text_returns_disabled_error_when_feature_flag_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EMOTION_INFERENCE_ENABLED", "false")
    _reset_settings_cache()
    client = TestClient(create_app())
    _login(client)

    response = client.post("/api/v1/emotions/text", json={"text": "I feel good"})

    assert response.status_code == 503
    body = response.json()
    assert body["detail"] == "emotion inference is disabled"
    assert body["error"]["code"] == "emotions.disabled"


def test_emotion_compatibility_text_route_returns_legacy_shape() -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post(
        "/emotion/text",
        json={"text": "I feel anxious and worried"},
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["emotion"], str)
    assert isinstance(body["confidence"], float)
    assert isinstance(body["emotions"], dict)
    assert body["source_type"] == "text"


def test_emotion_compatibility_routes_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMOTION_COMPAT_ROUTES_ENABLED", "false")
    _reset_settings_cache()
    client = TestClient(create_app())
    _login(client)

    response = client.post("/emotion/text", json={"text": "hello"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "emotions.compat_route_disabled"


def test_emotions_health_endpoint_is_public() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/emotions/health")

    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "degraded"}
