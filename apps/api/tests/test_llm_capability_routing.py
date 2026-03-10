"""Module for test llm capability routing."""

from dietary_guardian.infrastructure.ai.engine import InferenceEngine
from dietary_guardian.config.app import AppSettings as Settings
from dietary_guardian.infrastructure.llm import LLMCapability, LLMFactory, ModelProvider


def test_settings_parse_capability_targets_from_env_shape() -> None:
    settings = Settings(
        llm={
            "provider": "openai",
            "openai_api_key": "test-openai-key",
            "capability_targets": {
                "chatbot": {
                    "provider": "vllm",
                    "model": "aisingapore/sealion",
                    "base_url": "http://sealion.local/v1",
                }
            },
        },
    )

    target = settings.llm.capability_targets[LLMCapability.CHATBOT.value]

    assert target.provider == ModelProvider.VLLM.value
    assert target.model == "aisingapore/sealion"
    assert str(target.base_url) == "http://sealion.local/v1"


def test_factory_uses_capability_specific_target_over_global_provider() -> None:
    settings = Settings(
        llm={
            "provider": "openai",
            "openai_api_key": "test-openai-key",
            "openai_model": "gpt-4o-mini",
            "capability_targets": {
                "chatbot": {
                    "provider": "vllm",
                    "model": "aisingapore/sealion",
                    "base_url": "http://sealion.local/v1",
                }
            },
        },
    )

    model = LLMFactory.get_model(settings=settings, capability=LLMCapability.CHATBOT)

    assert getattr(model, "model_name", None) == "aisingapore/sealion"
    assert "http://sealion.local/v1" in LLMFactory.describe_model_destination(model)


def test_inference_engine_health_reports_capability_metadata() -> None:
    settings = Settings(
        llm={
            "provider": "openai",
            "openai_api_key": "test-openai-key",
            "capability_targets": {
                "meal_vision": {
                    "provider": "vllm",
                    "model": "vision-local",
                    "base_url": "http://vision.local/v1",
                }
            },
        },
    )

    engine = InferenceEngine(settings=settings, capability=LLMCapability.MEAL_VISION)
    health = engine.health()

    assert health.capability == LLMCapability.MEAL_VISION.value
    assert health.provider == ModelProvider.VLLM.value
    assert health.model == "vision-local"
    assert health.endpoint == "http://vision.local/v1"


def test_unmapped_capability_falls_back_to_legacy_global_settings() -> None:
    settings = Settings(llm={"provider": "openai", "openai_api_key": "test-openai-key", "openai_model": "gpt-4o-mini"})

    model = LLMFactory.get_model(settings=settings, capability=LLMCapability.CLINICAL_SUMMARY)

    assert getattr(model, "model_name", None) == "gpt-4o-mini"
    assert "endpoint=default" in LLMFactory.describe_model_destination(model)
