import os
from contextlib import suppress
from enum import StrEnum

from openai import AsyncOpenAI
from dietary_guardian.logging_config import get_logger
from pydantic import ValidationError
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.openai import OpenAIProvider

from dietary_guardian.config.runtime import LocalModelProfile
from dietary_guardian.config.settings import Settings, get_settings

ModelType = GoogleModel | OpenAIChatModel | TestModel
logger = get_logger(__name__)


class ModelProvider(StrEnum):
    GEMINI = "gemini"
    OPENAI = "openai"
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
    def _settings_default(field_name: str, fallback: str | float | int) -> str | float | int:
        with suppress(Exception):
            default = Settings.model_fields[field_name].default
            if default is not None:
                return default
        return fallback

    @staticmethod
    def _local_network_config() -> tuple[float, int]:
        try:
            settings = get_settings()
            return (
                float(settings.local_llm_request_timeout_seconds),
                int(settings.local_llm_transport_max_retries),
            )
        except ValidationError:
            timeout_default = str(LLMFactory._settings_default("local_llm_request_timeout_seconds", 1200.0))
            retries_default = str(LLMFactory._settings_default("local_llm_transport_max_retries", 0))
            timeout_raw = os.getenv("LOCAL_LLM_REQUEST_TIMEOUT_SECONDS", timeout_default)
            retries_raw = os.getenv("LOCAL_LLM_TRANSPORT_MAX_RETRIES", retries_default)
            with suppress(ValueError):
                timeout = float(timeout_raw)
                retries = int(retries_raw)
                return timeout, retries
            return float(timeout_default), int(retries_default)

    @staticmethod
    def _build_local_provider(base_url: str, api_key: str) -> OpenAIProvider:
        timeout_seconds, max_retries = LLMFactory._local_network_config()
        logger.info(
            "provider_local_network_config base_url=%s timeout_seconds=%.1f transport_max_retries=%s",
            base_url,
            timeout_seconds,
            max_retries,
        )
        try:
            openai_client = AsyncOpenAI(
                base_url=base_url,
                api_key=api_key,
                timeout=timeout_seconds,
                max_retries=max_retries,
            )
            return OpenAIProvider(openai_client=openai_client)
        except TypeError:
            logger.warning(
                "provider_local_network_config_compat_fallback base_url=%s reason=provider_constructor_does_not_accept_openai_client",
                base_url,
            )
            return OpenAIProvider(base_url=base_url, api_key=api_key)

    @staticmethod
    def _openai_network_config() -> tuple[float, int]:
        try:
            settings = get_settings()
            return (
                float(settings.openai_request_timeout_seconds),
                int(settings.openai_transport_max_retries),
            )
        except ValidationError:
            timeout_default = str(LLMFactory._settings_default("openai_request_timeout_seconds", 120.0))
            retries_default = str(LLMFactory._settings_default("openai_transport_max_retries", 2))
            timeout_raw = os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS", timeout_default)
            retries_raw = os.getenv("OPENAI_TRANSPORT_MAX_RETRIES", retries_default)
            with suppress(ValueError):
                timeout = float(timeout_raw)
                retries = int(retries_raw)
                return timeout, retries
            return float(timeout_default), int(retries_default)

    @staticmethod
    def _build_openai_provider(*, api_key: str, base_url: str | None) -> OpenAIProvider:
        timeout_seconds, max_retries = LLMFactory._openai_network_config()
        logger.info(
            "provider_openai_network_config base_url=%s timeout_seconds=%.1f transport_max_retries=%s",
            base_url or "default",
            timeout_seconds,
            max_retries,
        )
        try:
            openai_client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout_seconds,
                max_retries=max_retries,
            )
            return OpenAIProvider(openai_client=openai_client)
        except TypeError:
            logger.warning(
                "provider_openai_network_config_compat_fallback base_url=%s reason=provider_constructor_does_not_accept_openai_client",
                base_url or "default",
            )
            if base_url:
                return OpenAIProvider(base_url=base_url, api_key=api_key)
            return OpenAIProvider(api_key=api_key)

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
        provider = LLMFactory._build_local_provider(profile.base_url, api_key)
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

        if target_provider == ModelProvider.OPENAI.value:
            if settings is not None:
                api_key = settings.openai_api_key
                base_url = str(settings.openai_base_url) if settings.openai_base_url else None
                target_model = model_name or settings.openai_model
            else:
                api_key = os.getenv("OPENAI_API_KEY")
                base_url = os.getenv("OPENAI_BASE_URL")
                model_default = str(LLMFactory._settings_default("openai_model", "gpt-4o-mini"))
                target_model = model_name or os.getenv("OPENAI_MODEL", model_default)
            if not api_key:
                logger.warning("provider_openai_missing_api_key fallback=test")
                return LLMFactory._attach_model_name(TestModel(), "test-model")
            openai_provider = LLMFactory._build_openai_provider(api_key=api_key, base_url=base_url)
            model = OpenAIChatModel(target_model, provider=openai_provider)
            logger.info(
                "provider_selected provider=openai model=%s base_url=%s",
                target_model,
                base_url or "default",
            )
            return LLMFactory._attach_model_name(model, target_model)

        if target_provider in (ModelProvider.OLLAMA.value, ModelProvider.VLLM.value):
            if settings is not None:
                base_url = str(
                    settings.local_llm_base_url
                    or settings.ollama_base_url
                    or LLMFactory._settings_default("local_llm_base_url", "http://localhost:11434/v1")
                )
                api_key = settings.local_llm_api_key
                target_model = model_name or settings.local_llm_model
            else:
                base_url_default = str(LLMFactory._settings_default("local_llm_base_url", "http://localhost:11434/v1"))
                api_key_default = str(LLMFactory._settings_default("local_llm_api_key", "ollama"))
                model_default = str(LLMFactory._settings_default("local_llm_model", "llama3"))
                base_url = os.getenv("LOCAL_LLM_BASE_URL") or os.getenv("OLLAMA_BASE_URL") or base_url_default
                api_key = os.getenv("LOCAL_LLM_API_KEY", api_key_default)
                target_model = model_name or os.getenv("LOCAL_LLM_MODEL", model_default)
            local_provider = LLMFactory._build_local_provider(base_url, api_key)
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
