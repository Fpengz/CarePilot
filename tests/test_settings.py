import pytest
from pydantic import ValidationError

from dietary_guardian.config.settings import Settings, get_settings


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

    assert first.llm_provider == "test"
    assert second.llm_provider == "ollama"


def test_gemini_provider_requires_key() -> None:
    with pytest.raises(ValidationError):
        Settings(llm_provider="gemini", gemini_api_key=None, google_api_key=None)


def test_local_provider_allows_missing_gemini_key() -> None:
    settings = Settings(
        llm_provider="ollama",
        gemini_api_key=None,
        google_api_key=None,
        local_llm_base_url="http://localhost:11434/v1",
    )
    assert settings.llm_provider == "ollama"


def test_ollama_base_url_alias_normalization() -> None:
    settings = Settings(
        llm_provider="ollama",
        local_llm_base_url=None,
        ollama_base_url="http://localhost:11434/v1",
    )
    assert settings.local_llm_base_url == "http://localhost:11434/v1"


def test_vllm_base_url_alias_normalization() -> None:
    settings = Settings(
        llm_provider="vllm",
        local_llm_base_url=None,
        ollama_base_url="http://localhost:11434/v1",
    )
    assert settings.local_llm_base_url == "http://localhost:11434/v1"
