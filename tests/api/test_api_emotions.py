"""Module for test api emotions."""

from collections.abc import Generator

import pytest
from apps.api.carepilot_api.deps import build_app_context
from apps.api.carepilot_api.main import create_app
from fastapi.testclient import TestClient

from care_pilot.agent.emotion import EmotionAgent
from care_pilot.agent.emotion.schemas import (
    EmotionContextFeatures,
    EmotionInferenceResult,
    EmotionLabel,
    EmotionProductState,
    EmotionRuntimeHealth,
    FusionTrace,
    SpeechEmotionBranchResult,
    SpeechEmotionInput,
    TextEmotionBranchResult,
    TextEmotionInput,
)
from care_pilot.config.app import get_settings
from care_pilot.features.companion.emotion.ports import EmotionInferencePort


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _emotion_enabled_env(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "in_memory")
    monkeypatch.setenv("EMOTION_INFERENCE_ENABLED", "true")
    monkeypatch.setenv("EMOTION_SPEECH_ENABLED", "true")
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.com", "password": "member-pass"},
    )
    assert response.status_code == 200


class _StubEmotionPort(EmotionInferencePort):
    def infer_text(self, payload: TextEmotionInput) -> EmotionInferenceResult:
        context = EmotionContextFeatures(recent_labels=[], trend="stable")
        return EmotionInferenceResult(
            source_type="text",
            final_emotion=EmotionLabel.NEUTRAL,
            product_state=EmotionProductState.STABLE,
            confidence=0.7,
            fusion_method="stub",
            trace=FusionTrace(
                fusion_inputs={},
                weighting_strategy="stub",
                final_decision_reason="stub",
            ),
            text_branch=TextEmotionBranchResult(
                transcript_or_text=payload.text,
                model_name="stub-text",
                predicted_emotion=EmotionLabel.NEUTRAL,
                confidence=0.7,
                emotion_scores={EmotionLabel.NEUTRAL: 0.7},
            ),
            speech_branch=None,
            context_features=context,
        )

    def infer_speech(self, payload: SpeechEmotionInput) -> EmotionInferenceResult:
        context = EmotionContextFeatures(recent_labels=[], trend="stable")
        return EmotionInferenceResult(
            source_type="mixed",
            final_emotion=EmotionLabel.NEUTRAL,
            product_state=EmotionProductState.STABLE,
            confidence=0.7,
            fusion_method="stub",
            trace=FusionTrace(
                fusion_inputs={},
                weighting_strategy="stub",
                final_decision_reason="stub",
            ),
            text_branch=TextEmotionBranchResult(
                transcript_or_text=payload.transcription or "hello",
                model_name="stub-text",
                predicted_emotion=EmotionLabel.NEUTRAL,
                confidence=0.7,
                emotion_scores={EmotionLabel.NEUTRAL: 0.7},
            ),
            speech_branch=SpeechEmotionBranchResult(
                transcription=payload.transcription,
                model_name="stub-speech",
                predicted_emotion=EmotionLabel.NEUTRAL,
                confidence=0.6,
                emotion_scores={EmotionLabel.NEUTRAL: 0.6},
                acoustic_scores={"duration_sec": 1.0},
            ),
            context_features=context,
        )

    def health(self) -> EmotionRuntimeHealth:
        return EmotionRuntimeHealth(status="ready", model_cache_ready=True, source_commit="sha")


def _client(*, inference_enabled: bool = True, speech_enabled: bool = True) -> TestClient:
    ctx = build_app_context()
    ctx.emotion_agent = EmotionAgent(
        runtime=_StubEmotionPort(),
        inference_enabled=inference_enabled,
        speech_enabled=speech_enabled,
        request_timeout_seconds=1.0,
    )
    return TestClient(create_app(ctx))


def test_emotions_text_requires_auth() -> None:
    client = _client(inference_enabled=False, speech_enabled=False)

    response = client.post("/api/v1/emotions/text", json={"text": "I feel good"})

    assert response.status_code == 401


def test_emotions_text_returns_observation() -> None:
    client = _client()
    _login(client)

    response = client.post(
        "/api/v1/emotions/text",
        json={"text": "I am really happy and calm after lunch."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["observation"]["source_type"] == "text"
    assert body["observation"]["final_emotion"] in {"neutral", "happy"}
    assert body["observation"]["product_state"] == "stable"


def test_emotions_speech_returns_observation() -> None:
    client = _client()
    _login(client)

    response = client.post(
        "/api/v1/emotions/speech",
        files={"file": ("sample.wav", b"fake-wave-data", "audio/wav")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["observation"]["source_type"] == "mixed"
    assert body["observation"]["product_state"] == "stable"


def test_emotions_text_returns_disabled_error_when_feature_flag_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EMOTION_INFERENCE_ENABLED", "false")
    _reset_settings_cache()
    client = _client(inference_enabled=False, speech_enabled=False)
    _login(client)

    response = client.post("/api/v1/emotions/text", json={"text": "I feel good"})

    assert response.status_code == 503
    body = response.json()
    assert body["detail"] == "emotion inference is disabled"
    assert body["error"]["code"] == "emotions.disabled"


def test_emotion_legacy_route_is_removed() -> None:
    client = _client()
    _login(client)

    response = client.post("/emotion/text", json={"text": "I feel anxious and worried"})

    assert response.status_code == 404


def test_emotions_health_endpoint_is_public() -> None:
    client = _client()

    response = client.get("/api/v1/emotions/health")

    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "degraded"}


def test_emotions_health_returns_disabled_when_feature_flag_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EMOTION_INFERENCE_ENABLED", "false")
    _reset_settings_cache()
    client = _client(inference_enabled=False, speech_enabled=False)

    response = client.get("/api/v1/emotions/health")

    assert response.status_code == 200
    assert response.json()["status"] == "disabled"
