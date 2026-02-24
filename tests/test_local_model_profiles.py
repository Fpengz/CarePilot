from dietary_guardian.agents.provider_factory import LLMFactory
from dietary_guardian.config.runtime import AppConfig, LocalModelProfile


def test_default_local_model_profiles_are_available() -> None:
    config = AppConfig()
    profiles = config.local_models.profiles

    assert "ollama_llama3" in profiles
    assert "vllm_qwen" in profiles
    assert profiles["ollama_llama3"].provider == "ollama"
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
