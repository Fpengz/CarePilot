"""Tests for settings."""

import pytest
from pydantic import ValidationError

from dietary_guardian.config.app import AppSettings as Settings, get_settings


def test_settings_cache_returns_same_instance(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "test")
    first = get_settings()
    second = get_settings()
    assert first is second


def test_settings_cache_clear_reloads_env(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "test")
    first = get_settings()

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    get_settings.cache_clear()
    second = get_settings()

    assert first.llm.provider == "test"
    assert second.llm.provider == "ollama"


def test_gemini_provider_requires_key() -> None:
    with pytest.raises(ValidationError):
        Settings(llm={"provider": "gemini", "gemini_api_key": None, "google_api_key": None})


def test_local_provider_allows_missing_gemini_key() -> None:
    settings = Settings(
        llm={
            "provider": "ollama",
            "gemini_api_key": None,
            "google_api_key": None,
            "local_llm_base_url": "http://localhost:11434/v1",
        }
    )
    assert settings.llm.provider == "ollama"


def test_legacy_compatibility_settings_are_removed() -> None:
    assert "ollama_base_url" not in Settings.model_fields
    assert "redis_keyspace_version" not in Settings.model_fields
    assert "emotion_compat_routes_enabled" not in Settings.model_fields


def test_openai_provider_requires_key() -> None:
    with pytest.raises(ValidationError):
        Settings(llm={"provider": "openai", "openai_api_key": None})


def test_openai_provider_allows_with_key() -> None:
    settings = Settings(llm={"provider": "openai", "openai_api_key": "test-openai-key"})
    assert settings.llm.provider == "openai"


def test_runtime_backend_settings_support_sqlite_and_optional_redis() -> None:
    settings = Settings(
        llm={"provider": "test"},
        storage={"ephemeral_state_backend": "redis", "redis_url": "redis://localhost:6379/0"},
    )
    assert settings.storage.app_data_backend == "sqlite"
    assert settings.auth.store_backend == "sqlite"
    assert settings.storage.household_store_backend == "sqlite"
    assert settings.storage.ephemeral_state_backend == "redis"


def test_app_env_defaults_readiness_strictness_by_profile() -> None:
    dev_settings = Settings(llm={"provider": "test"}, app={"env": "dev"})
    prod_settings = Settings(
        llm={"provider": "test"},
        app={"env": "prod"},
        auth={"session_secret": "prod-secret", "cookie_secure": True},
    )

    assert dev_settings.observability.readiness_fail_on_warnings is False
    assert prod_settings.observability.readiness_fail_on_warnings is True


def test_app_env_allows_explicit_readiness_strictness_override() -> None:
    settings = Settings(
        llm={"provider": "test"},
        app={"env": "dev"},
        observability={"readiness_fail_on_warnings": True},
    )
    assert settings.observability.readiness_fail_on_warnings is True


def test_non_dev_rejects_default_session_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(llm={"provider": "test"}, app={"env": "staging"})

    with pytest.raises(ValidationError):
        Settings(llm={"provider": "test"}, app={"env": "prod"})


def test_non_dev_requires_secure_cookie() -> None:
    with pytest.raises(ValidationError):
        Settings(
            llm={"provider": "test"},
            app={"env": "prod"},
            auth={"session_secret": "prod-secret", "cookie_secure": False},
        )

    settings = Settings(
        llm={"provider": "test"},
        app={"env": "prod"},
        auth={"session_secret": "prod-secret", "cookie_secure": True},
    )
    assert settings.auth.cookie_secure is True


def test_cookie_samesite_none_requires_secure_cookie() -> None:
    with pytest.raises(ValidationError):
        Settings(
            llm={"provider": "test"},
            app={"env": "dev"},
            auth={"cookie_samesite": "none", "cookie_secure": False},
        )

    settings = Settings(
        llm={"provider": "test"},
        app={"env": "dev"},
        auth={"cookie_samesite": "none", "cookie_secure": True},
    )
    assert settings.auth.cookie_samesite == "none"


def test_auth_seed_demo_users_default_and_non_dev_guardrails() -> None:
    dev_settings = Settings(llm={"provider": "test"}, app={"env": "dev"})
    assert dev_settings.auth.seed_demo_users is True

    prod_settings = Settings(
        llm={"provider": "test"},
        app={"env": "prod"},
        auth={"session_secret": "prod-secret", "cookie_secure": True},
    )
    assert prod_settings.auth.seed_demo_users is False

    with pytest.raises(ValidationError):
        Settings(
            llm={"provider": "test"},
            app={"env": "prod"},
            auth={"session_secret": "prod-secret", "cookie_secure": True, "seed_demo_users": True},
        )


def test_prod_normalizes_tool_policy_mode_to_enforce() -> None:
    settings = Settings(
        llm={"provider": "test"},
        app={"env": "prod"},
        auth={"session_secret": "prod-secret", "cookie_secure": True},
        workers={"tool_policy_enforcement_mode": "shadow"},
    )
    assert settings.workers.tool_policy_enforcement_mode == "enforce"


def test_legacy_postgres_backend_settings_are_removed() -> None:
    assert "postgres_dsn" not in Settings.model_fields
    with pytest.raises(ValidationError):
        Settings(llm={"provider": "test"}, storage={"app_data_backend": "postgres"})
    with pytest.raises(ValidationError):
        Settings(llm={"provider": "test"}, auth={"store_backend": "postgres"})
    with pytest.raises(ValidationError):
        Settings(llm={"provider": "test"}, storage={"household_store_backend": "postgres"})


def test_external_worker_mode_requires_redis_ephemeral_backend() -> None:
    with pytest.raises(ValidationError):
        Settings(
            llm={"provider": "test"},
            workers={"worker_mode": "external"},
            storage={"ephemeral_state_backend": "in_memory"},
        )

    settings = Settings(
        llm={"provider": "test"},
        workers={"worker_mode": "external"},
        storage={"ephemeral_state_backend": "redis", "redis_url": "redis://localhost:6379/0"},
    )
    assert settings.workers.worker_mode == "external"
