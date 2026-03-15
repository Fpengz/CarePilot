"""Module for test llm capability routing."""

from care_pilot.config.app import AppSettings as Settings
import json

from care_pilot.config.llm import LLMCapability, ModelProvider
from care_pilot.config.app import get_settings
from apps.api.carepilot_api.deps import build_app_context, close_app_context
from care_pilot.agent.runtime.inference_engine import InferenceEngine
from care_pilot.agent.runtime.llm_factory import LLMFactory


def test_settings_parse_capability_targets_from_env_shape() -> None:
    settings = _build_settings(
        llm={
            "provider": "openai",
            "openai_api_key": "test-openai-key",
            "capability_map": {
                "chatbot": {
                    "provider": "vllm",
                    "model": "aisingapore/sealion",
                    "base_url": "http://sealion.local/v1",
                }
            },
        },
    )

    target = settings.llm.capability_map[LLMCapability.CHATBOT]

    assert target.provider == ModelProvider.VLLM.value
    assert target.model == "aisingapore/sealion"
    assert str(target.base_url) == "http://sealion.local/v1"


def test_factory_uses_capability_specific_target_over_global_provider() -> None:
    settings = _build_settings(
        llm={
            "provider": "openai",
            "openai_api_key": "test-openai-key",
            "openai_model": "gpt-4o-mini",
            "capability_map": {
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
    settings = _build_settings(
        llm={
            "provider": "openai",
            "openai_api_key": "test-openai-key",
            "capability_map": {
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
    settings = _build_settings(
        llm={
            "provider": "openai",
            "openai_api_key": "test-openai-key",
            "openai_model": "gpt-4o-mini",
        }
    )

    model = LLMFactory.get_model(settings=settings, capability=LLMCapability.CLINICAL_SUMMARY)

    assert getattr(model, "model_name", None) == "gpt-4o-mini"
    assert "endpoint=default" in LLMFactory.describe_model_destination(model)


def test_app_context_medication_parse_uses_base_provider(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv(
        "LLM_CAPABILITY_TARGETS",
        json.dumps(
            {
                "medication_parse": {
                    "provider": "vllm",
                    "model": "med-parse-v1",
                    "base_url": "http://med.local/v1",
                    "api_key": "local-test-key",
                }
            }
        ),
    )

    ctx = build_app_context()
    try:
        health = ctx.medication_inference_engine.health()
    finally:
        close_app_context(ctx)

    assert health.capability == LLMCapability.MEDICATION_PARSE.value
    assert health.provider == ModelProvider.OPENAI.value
    assert health.model == "gpt-4o-mini"


def _build_settings(**overrides: object) -> Settings:
    return Settings.model_validate(overrides)
