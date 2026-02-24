import os
from enum import Enum
from typing import Optional, Union

from dietary_guardian.logging_config import get_logger
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.openai import OpenAIProvider

from dietary_guardian.config.runtime import LocalModelProfile

ModelType = Union[GoogleModel, OpenAIChatModel, TestModel]
logger = get_logger(__name__)


class ModelProvider(str, Enum):
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
        try:
            setattr(model, "model_name", model_name)
        except Exception:
            pass
        return model

    @staticmethod
    def from_profile(profile: LocalModelProfile) -> ModelType:
        if not profile.enabled:
            logger.warning("provider_profile_disabled profile_id=%s", profile.id)
            return LLMFactory._attach_model_name(TestModel(), "test-model")

        api_key = os.getenv(profile.api_key_env) or os.getenv("LOCAL_LLM_API_KEY", "ollama")
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
    def get_model(provider: Optional[str] = None, model_name: Optional[str] = None) -> ModelType:
        target_provider = provider or os.getenv("LLM_PROVIDER", ModelProvider.GEMINI.value)

        if target_provider == ModelProvider.TEST.value:
            logger.info("provider_selected provider=test model=%s", model_name or "test-model")
            return LLMFactory._attach_model_name(TestModel(), model_name or "test-model")

        if target_provider == ModelProvider.GEMINI.value:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.warning("provider_gemini_missing_api_key fallback=test")
                return LLMFactory._attach_model_name(TestModel(), "test-model")
            os.environ.setdefault("GOOGLE_API_KEY", api_key)
            target_model = model_name or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            model = GoogleModel(target_model)
            logger.info("provider_selected provider=gemini model=%s", target_model)
            return LLMFactory._attach_model_name(model, target_model)

        if target_provider in (ModelProvider.OLLAMA.value, ModelProvider.VLLM.value):
            base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
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
