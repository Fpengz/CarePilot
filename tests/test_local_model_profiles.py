from typing import cast

from dietary_guardian.agents.provider_factory import LLMFactory
from dietary_guardian.config.settings import get_settings
from dietary_guardian.config.runtime import AppConfig, LocalModelProfile


def test_default_local_model_profiles_are_available() -> None:
    config = AppConfig()
    profiles = config.local_models.profiles

    assert "ollama_qwen3-vl:4b" in profiles
    assert "vllm_qwen" in profiles
    assert profiles["ollama_qwen3-vl:4b"].provider == "ollama"
    assert profiles["vllm_qwen"].provider == "vllm"


def test_from_profile_uses_profile_settings() -> None:
    profile = LocalModelProfile(
        id="local-test",
        provider="ollama",
        model_name="llama3",
        base_url="http://localhost:11434/v1",
        api_key_env="LOCAL_LLM_API_KEY",
        enabled=True,
    )
    model = LLMFactory.from_profile(profile)
    assert getattr(model, "model_name", "") == "llama3"


def test_disabled_profile_falls_back_to_test_model() -> None:
    profile = LocalModelProfile(
        id="disabled",
        provider="vllm",
        model_name="Qwen/Qwen2.5-7B-Instruct",
        base_url="http://localhost:8000/v1",
        enabled=False,
    )
    model = LLMFactory.from_profile(profile)
    assert "TestModel" in model.__class__.__name__


def test_get_model_uses_settings_default_provider(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "test")
    get_settings.cache_clear()
    model = LLMFactory.get_model()
    assert "TestModel" in model.__class__.__name__
    get_settings.cache_clear()


def test_get_model_explicit_args_override_settings(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "test")
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "qwen3-vl:4b")
    get_settings.cache_clear()
    model = LLMFactory.get_model(provider="ollama", model_name="override-model")
    assert getattr(model, "model_name", "") == "override-model"
    get_settings.cache_clear()


def test_get_model_explicit_test_provider_bypasses_invalid_global_settings(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    get_settings.cache_clear()

    model = LLMFactory.get_model(provider="test")
    assert "TestModel" in model.__class__.__name__
    get_settings.cache_clear()


def test_get_model_explicit_ollama_provider_bypasses_invalid_global_settings(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "ollama")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "qwen3-vl:4b")
    get_settings.cache_clear()

    model = LLMFactory.get_model(provider="ollama")
    assert getattr(model, "model_name", "") == "qwen3-vl:4b"
    get_settings.cache_clear()


def test_profile_uses_profile_specific_api_key_env(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeProvider:
        def __init__(self, base_url: str, api_key: str) -> None:
            captured["base_url"] = base_url
            captured["api_key"] = api_key

    class FakeModel:
        def __init__(self, model_name: str, provider: FakeProvider) -> None:
            self.model_name = model_name
            self.provider = provider

    monkeypatch.setattr("dietary_guardian.agents.provider_factory.OpenAIProvider", FakeProvider)
    monkeypatch.setattr("dietary_guardian.agents.provider_factory.OpenAIChatModel", FakeModel)
    monkeypatch.setenv("CUSTOM_PROFILE_API_KEY", "profile-secret")
    monkeypatch.delenv("LOCAL_LLM_API_KEY", raising=False)
    get_settings.cache_clear()
    profile = LocalModelProfile(
        id="custom",
        provider="vllm",
        model_name="Qwen/Qwen2.5-7B-Instruct",
        base_url="http://localhost:8000/v1",
        api_key_env="CUSTOM_PROFILE_API_KEY",
        enabled=True,
    )

    model = LLMFactory.from_profile(profile)
    assert getattr(model, "model_name", None) == "Qwen/Qwen2.5-7B-Instruct"
    assert captured["base_url"] == "http://localhost:8000/v1"
    assert captured["api_key"] == "profile-secret"
    get_settings.cache_clear()


def test_profile_creation_does_not_require_global_provider_validation(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeProvider:
        def __init__(self, base_url: str, api_key: str) -> None:
            captured["base_url"] = base_url
            captured["api_key"] = api_key

    class FakeModel:
        def __init__(self, model_name: str, provider: FakeProvider) -> None:
            self.model_name = model_name
            self.provider = provider

    monkeypatch.setattr("dietary_guardian.agents.provider_factory.OpenAIProvider", FakeProvider)
    monkeypatch.setattr("dietary_guardian.agents.provider_factory.OpenAIChatModel", FakeModel)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("CUSTOM_PROFILE_API_KEY", "profile-secret")
    get_settings.cache_clear()

    profile = LocalModelProfile(
        id="local-only",
        provider="ollama",
        model_name="llama3",
        base_url="http://localhost:11434/v1",
        api_key_env="CUSTOM_PROFILE_API_KEY",
        enabled=True,
    )

    model = LLMFactory.from_profile(profile)
    assert getattr(model, "model_name", None) == "llama3"
    assert captured["base_url"] == "http://localhost:11434/v1"
    assert captured["api_key"] == "profile-secret"
    get_settings.cache_clear()


def test_local_provider_uses_configured_timeout_and_transport_retries(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):  # noqa: ANN003
            captured["async_openai_kwargs"] = kwargs

    class FakeProvider:
        def __init__(self, *, openai_client=None, **kwargs):  # noqa: ANN003
            captured["openai_client"] = openai_client
            captured["provider_kwargs"] = kwargs
            self.base_url = "http://localhost:11434/v1"

    class FakeModel:
        def __init__(self, model_name: str, provider: FakeProvider) -> None:
            self.model_name = model_name
            self.provider = provider

    monkeypatch.setattr("dietary_guardian.agents.provider_factory.AsyncOpenAI", FakeAsyncOpenAI)
    monkeypatch.setattr("dietary_guardian.agents.provider_factory.OpenAIProvider", FakeProvider)
    monkeypatch.setattr("dietary_guardian.agents.provider_factory.OpenAIChatModel", FakeModel)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "qwen3-vl:4b")
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "ollama")
    monkeypatch.setenv("LOCAL_LLM_REQUEST_TIMEOUT_SECONDS", "1200")
    monkeypatch.setenv("LOCAL_LLM_TRANSPORT_MAX_RETRIES", "0")
    get_settings.cache_clear()

    model = LLMFactory.get_model(provider="ollama")

    assert getattr(model, "model_name", None) == "qwen3-vl:4b"
    kwargs = cast(dict[str, object], captured["async_openai_kwargs"])
    assert kwargs["timeout"] == 1200.0
    assert kwargs["max_retries"] == 0
    get_settings.cache_clear()


def test_get_model_explicit_openai_provider_uses_openai_settings(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):  # noqa: ANN003
            captured["async_openai_kwargs"] = kwargs

    class FakeProvider:
        def __init__(self, *, openai_client=None, **kwargs):  # noqa: ANN003
            captured["openai_client"] = openai_client
            captured["provider_kwargs"] = kwargs
            self.base_url = "https://api.openai.com/v1"

    class FakeModel:
        def __init__(self, model_name: str, provider: FakeProvider) -> None:
            self.model_name = model_name
            self.provider = provider

    monkeypatch.setattr("dietary_guardian.agents.provider_factory.AsyncOpenAI", FakeAsyncOpenAI)
    monkeypatch.setattr("dietary_guardian.agents.provider_factory.OpenAIProvider", FakeProvider)
    monkeypatch.setattr("dietary_guardian.agents.provider_factory.OpenAIChatModel", FakeModel)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_REQUEST_TIMEOUT_SECONDS", "90")
    monkeypatch.setenv("OPENAI_TRANSPORT_MAX_RETRIES", "2")
    get_settings.cache_clear()

    model = LLMFactory.get_model(provider="openai")

    assert getattr(model, "model_name", None) == "gpt-4o-mini"
    kwargs = cast(dict[str, object], captured["async_openai_kwargs"])
    assert kwargs["api_key"] == "sk-test"
    assert kwargs["timeout"] == 90.0
    assert kwargs["max_retries"] == 2
    get_settings.cache_clear()
