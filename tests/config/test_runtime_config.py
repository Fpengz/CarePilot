"""Tests for runtime config — modern equivalents of legacy AppConfig/MedicalConfig/ModelSettings."""

import pytest

from dietary_guardian.config.app import AppSettings, get_settings
from dietary_guardian.config.llm import InferenceConfig, LLMSettings


def test_llm_inference_defaults() -> None:
    llm = LLMSettings()
    inf = llm.inference
    assert isinstance(inf, InferenceConfig)
    assert inf.wall_clock_timeout_seconds == 180.0
    assert inf.cloud_output_validation_retries == 1
    assert inf.local_output_validation_retries == 0
    assert inf.use_engine_v2 is True


def test_llm_inference_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_INFERENCE_WALL_CLOCK_TIMEOUT_SECONDS", "60.0")
    monkeypatch.setenv("LLM_CLOUD_OUTPUT_VALIDATION_RETRIES", "2")
    llm = LLMSettings()
    assert llm.inference.wall_clock_timeout_seconds == 60.0
    assert llm.inference.cloud_output_validation_retries == 2


def test_auth_settings_defaults() -> None:
    get_settings.cache_clear()
    settings = AppSettings()
    assert settings.auth.session_ttl_seconds == 86400
    assert settings.auth.login_max_failed_attempts == 5
    assert settings.auth.store_backend == "sqlite"


def test_worker_settings_defaults() -> None:
    settings = AppSettings()
    assert settings.workers.reminder_scheduler_interval_seconds == 30
    assert settings.workers.outbox_worker_poll_interval_seconds == 5


def test_api_settings_defaults() -> None:
    settings = AppSettings()
    assert settings.api.port == 8001
    assert settings.api.rate_limit_enabled is True
