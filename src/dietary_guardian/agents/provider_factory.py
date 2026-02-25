import os
from contextlib import suppress
from enum import StrEnum

from dietary_guardian.logging_config import get_logger
from pydantic import ValidationError
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.openai import OpenAIProvider

from dietary_guardian.config.runtime import LocalModelProfile
from dietary_guardian.config.settings import get_settings

ModelType = GoogleModel | OpenAIChatModel | TestModel
logger = get_logger(__name__)


class ModelProvider(StrEnum):
    GEMINI = "gemini"
    OLLAMA = "ollama"
    VLLM = "vllm"
    TEST = "test"


class LLMFactory:
    """
    Factory for instantiating LLM models based on environment configuration.
    """

    @staticmethod
    def _attach_model_name(model: ModelType, model_name: str) -> ModelType:
        with suppress(Exception):
            setattr(model, "model_name", model_name)
        return model

    @staticmethod
    def describe_model_destination(model: ModelType) -> str:
        model_name = getattr(model, "model_name", getattr(model, "model", "unknown"))
        provider_obj = getattr(model, "provider", getattr(model, "_provider", None))
        base_url = None
        if provider_obj is not None:
            base_url = getattr(provider_obj, "base_url", None)
        if base_url:
            return f"model={model_name} endpoint={base_url}"
        return f"model={model_name} endpoint=default"

    @staticmethod
    def from_profile(profile: LocalModelProfile) -> ModelType:
        if not profile.enabled:
            logger.warning("provider_profile_disabled profile_id=%s", profile.id)
            return LLMFactory._attach_model_name(TestModel(), "test-model")

        api_key = os.getenv(profile.api_key_env) or os.getenv("LOCAL_LLM_API_KEY")
        if not api_key:
            try:
                api_key = get_settings().local_llm_api_key
            except ValidationError:
                api_key = "ollama"
        provider = OpenAIProvider(base_url=profile.base_url, api_key=api_key)
        model = OpenAIChatModel(profile.model_name, provider=provider)
        logger.info(
            "provider_from_profile profile_id=%s provider=%s model=%s base_url=%s",
            profile.id,
            profile.provider,
            profile.model_name,
            profile.base_url,
        )
        return LLMFactory._attach_model_name(model, profile.model_name)

    @staticmethod
    def get_model(provider: str | None = None, model_name: str | None = None) -> ModelType:
        settings = None
        if provider is None:
            settings = get_settings()
            target_provider = settings.llm_provider
        else:
            target_provider = provider

        if target_provider == ModelProvider.TEST.value:
            logger.info("provider_selected provider=test model=%s", model_name or "test-model")
            return LLMFactory._attach_model_name(TestModel(), model_name or "test-model")

        if target_provider == ModelProvider.GEMINI.value:
            api_key = (
                settings.effective_google_api_key
                if settings is not None
                else (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
            )
            if not api_key:
                logger.warning("provider_gemini_missing_api_key fallback=test")
                return LLMFactory._attach_model_name(TestModel(), "test-model")
            os.environ.setdefault("GOOGLE_API_KEY", api_key)
            target_model = model_name or (
                settings.gemini_model if settings is not None else os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            )
            model = GoogleModel(target_model)
            logger.info("provider_selected provider=gemini model=%s", target_model)
            return LLMFactory._attach_model_name(model, target_model)

        if target_provider in (ModelProvider.OLLAMA.value, ModelProvider.VLLM.value):
            if settings is not None:
                base_url = str(
                    settings.local_llm_base_url or settings.ollama_base_url or "http://localhost:11434/v1"
                )
                api_key = settings.local_llm_api_key
                target_model = model_name or settings.local_llm_model
            else:
                base_url = os.getenv("LOCAL_LLM_BASE_URL") or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1"
                api_key = os.getenv("LOCAL_LLM_API_KEY", "ollama")
                target_model = model_name or os.getenv("LOCAL_LLM_MODEL", "llama3")
            local_provider = OpenAIProvider(base_url=base_url, api_key=api_key)
            model = OpenAIChatModel(target_model, provider=local_provider)
            logger.info(
                "provider_selected provider=%s model=%s base_url=%s",
                target_provider,
                target_model,
                base_url,
            )
            return LLMFactory._attach_model_name(model, target_model)

        logger.warning("provider_unknown provider=%s fallback=test", target_provider)
        return LLMFactory._attach_model_name(TestModel(), "test-model")
