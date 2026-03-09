"""Provider factory for constructing concrete LLM clients and model runtimes."""

import os
from contextlib import suppress

from openai import AsyncOpenAI
from pydantic import ValidationError
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.openai import OpenAIProvider

from dietary_guardian.config.app import AppSettings, get_settings
from dietary_guardian.config.llm import LLMCapability, LLMSettings, LocalModelProfile, ModelProvider
from dietary_guardian.llm.routing import LLMCapabilityRouter
from dietary_guardian.llm.types import ResolvedModelRuntime
from dietary_guardian.logging_config import get_logger

ModelType = GoogleModel | OpenAIChatModel | TestModel
logger = get_logger(__name__)


class LLMFactory:
    @staticmethod
    def _attach_model_name(model: ModelType, model_name: str) -> ModelType:
        with suppress(Exception):
            setattr(model, "model_name", model_name)
        return model

    @staticmethod
    def _settings_default(field_name: str, fallback: str | float | int) -> str | float | int:
        with suppress(Exception):
            default = LLMSettings.model_fields[field_name].default
            if default is not None:
                return default
        return fallback

    @staticmethod
    def _local_network_config() -> tuple[float, int]:
        try:
            settings = get_settings()
            return (
                float(settings.llm.local_llm_request_timeout_seconds),
                int(settings.llm.local_llm_transport_max_retries),
            )
        except ValidationError:
            timeout_default = str(LLMFactory._settings_default("local_llm_request_timeout_seconds", 1200.0))
            retries_default = str(LLMFactory._settings_default("local_llm_transport_max_retries", 0))
            timeout_raw = os.getenv("LOCAL_LLM_REQUEST_TIMEOUT_SECONDS", timeout_default)
            retries_raw = os.getenv("LOCAL_LLM_TRANSPORT_MAX_RETRIES", retries_default)
            with suppress(ValueError):
                return float(timeout_raw), int(retries_raw)
            return float(timeout_default), int(retries_default)

    @staticmethod
    def _openai_network_config() -> tuple[float, int]:
        try:
            settings = get_settings()
            return (
                float(settings.llm.openai_request_timeout_seconds),
                int(settings.llm.openai_transport_max_retries),
            )
        except ValidationError:
            timeout_default = str(LLMFactory._settings_default("openai_request_timeout_seconds", 120.0))
            retries_default = str(LLMFactory._settings_default("openai_transport_max_retries", 2))
            timeout_raw = os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS", timeout_default)
            retries_raw = os.getenv("OPENAI_TRANSPORT_MAX_RETRIES", retries_default)
            with suppress(ValueError):
                return float(timeout_raw), int(retries_raw)
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
            return f"model={model_name} endpoint={str(base_url).rstrip('/')}"
        return f"model={model_name} endpoint=default"

    @staticmethod
    def from_profile(profile: LocalModelProfile) -> ModelType:
        if not profile.enabled:
            logger.warning("provider_profile_disabled profile_id=%s", profile.id)
            return LLMFactory._attach_model_name(TestModel(), "test-model")

        api_key = os.getenv(profile.api_key_env) or os.getenv("LOCAL_LLM_API_KEY")
        if not api_key:
            try:
                api_key = get_settings().llm.local_llm_api_key
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
    def _resolve_runtime(
        *,
        settings: AppSettings | None = None,
        provider: str | None = None,
        model_name: str | None = None,
        capability: LLMCapability | str | None = None,
    ) -> ResolvedModelRuntime:
        runtime_settings = settings
        if runtime_settings is None and provider is None:
            runtime_settings = get_settings()

        if provider is None:
            assert runtime_settings is not None
            routed = LLMCapabilityRouter(runtime_settings).resolve(capability)
            if routed is not None:
                if model_name is not None:
                    return ResolvedModelRuntime(
                        provider=routed.provider,
                        model_name=model_name,
                        capability=routed.capability,
                        base_url=routed.base_url,
                        api_key=routed.api_key,
                    )
                return routed
            target_provider = runtime_settings.llm.provider
        else:
            target_provider = provider

        if target_provider == ModelProvider.TEST.value:
            return ResolvedModelRuntime(
                provider=ModelProvider.TEST.value,
                model_name=model_name or "test-model",
                capability=capability.value if isinstance(capability, LLMCapability) else capability,
            )
        if target_provider == ModelProvider.GEMINI.value:
            api_key = (
                runtime_settings.llm.effective_google_api_key
                if runtime_settings is not None
                else (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
            )
            return ResolvedModelRuntime(
                provider=ModelProvider.GEMINI.value,
                model_name=model_name
                or (
                    runtime_settings.llm.gemini_model
                    if runtime_settings is not None
                    else str(LLMFactory._settings_default("gemini_model", "gemini-1.5-flash"))
                ),
                capability=capability.value if isinstance(capability, LLMCapability) else capability,
                api_key=api_key,
            )
        if target_provider == ModelProvider.OPENAI.value:
            return ResolvedModelRuntime(
                provider=ModelProvider.OPENAI.value,
                model_name=model_name
                or (
                    runtime_settings.llm.openai_model
                    if runtime_settings is not None
                    else str(LLMFactory._settings_default("openai_model", "gpt-4o-mini"))
                ),
                capability=capability.value if isinstance(capability, LLMCapability) else capability,
                base_url=(
                    str(runtime_settings.llm.openai_base_url)
                    if runtime_settings is not None and runtime_settings.llm.openai_base_url
                    else os.getenv("OPENAI_BASE_URL")
                ),
                api_key=(runtime_settings.llm.openai_api_key if runtime_settings is not None else None)
                or os.getenv("OPENAI_API_KEY"),
            )
        if target_provider in (ModelProvider.OLLAMA.value, ModelProvider.VLLM.value):
            return ResolvedModelRuntime(
                provider=target_provider,
                model_name=model_name
                or (
                    runtime_settings.llm.local_llm_model
                    if runtime_settings is not None
                    else str(LLMFactory._settings_default("local_llm_model", "qwen3-vl:4b"))
                ),
                capability=capability.value if isinstance(capability, LLMCapability) else capability,
                base_url=(
                    str(runtime_settings.llm.local_llm_base_url)
                    if runtime_settings is not None and runtime_settings.llm.local_llm_base_url
                    else os.getenv("LOCAL_LLM_BASE_URL")
                ),
                api_key=(runtime_settings.llm.local_llm_api_key if runtime_settings is not None else None)
                or os.getenv("LOCAL_LLM_API_KEY"),
            )
        if target_provider == ModelProvider.CODEX.value:
            return ResolvedModelRuntime(
                provider=ModelProvider.CODEX.value,
                model_name=model_name
                or (
                    runtime_settings.llm.openai_model
                    if runtime_settings is not None
                    else str(LLMFactory._settings_default("openai_model", "gpt-4o-mini"))
                ),
                capability=capability.value if isinstance(capability, LLMCapability) else capability,
            )
        return ResolvedModelRuntime(provider=ModelProvider.TEST.value, model_name="test-model")

    @staticmethod
    def get_model(
        provider: str | None = None,
        model_name: str | None = None,
        *,
        settings: AppSettings | None = None,
        capability: LLMCapability | str | None = None,
    ) -> ModelType:
        runtime = LLMFactory._resolve_runtime(
            settings=settings,
            provider=provider,
            model_name=model_name,
            capability=capability,
        )
        if runtime.provider == ModelProvider.TEST.value:
            logger.info("provider_selected provider=test model=%s capability=%s", runtime.model_name, runtime.capability or "none")
            return LLMFactory._attach_model_name(TestModel(), runtime.model_name)
        if runtime.provider == ModelProvider.GEMINI.value:
            api_key = runtime.api_key
            if not api_key:
                logger.warning("provider_gemini_missing_api_key fallback=test")
                return LLMFactory._attach_model_name(TestModel(), "test-model")
            os.environ.setdefault("GOOGLE_API_KEY", api_key)
            model = GoogleModel(runtime.model_name)
            logger.info("provider_selected provider=gemini model=%s capability=%s", runtime.model_name, runtime.capability or "none")
            return LLMFactory._attach_model_name(model, runtime.model_name)
        if runtime.provider == ModelProvider.OPENAI.value:
            api_key = runtime.api_key
            if not api_key:
                logger.warning("provider_openai_missing_api_key fallback=test")
                return LLMFactory._attach_model_name(TestModel(), "test-model")
            provider_obj = LLMFactory._build_openai_provider(api_key=api_key, base_url=runtime.base_url)
            model = OpenAIChatModel(runtime.model_name, provider=provider_obj)
            logger.info(
                "provider_selected provider=openai model=%s base_url=%s capability=%s",
                runtime.model_name,
                runtime.base_url or "default",
                runtime.capability or "none",
            )
            return LLMFactory._attach_model_name(model, runtime.model_name)
        if runtime.provider in (ModelProvider.OLLAMA.value, ModelProvider.VLLM.value):
            base_url = runtime.base_url or str(LLMFactory._settings_default("local_llm_base_url", "http://localhost:11434/v1"))
            api_key = runtime.api_key or str(LLMFactory._settings_default("local_llm_api_key", "ollama"))
            provider_obj = LLMFactory._build_local_provider(base_url, api_key)
            model = OpenAIChatModel(runtime.model_name, provider=provider_obj)
            logger.info(
                "provider_selected provider=%s model=%s base_url=%s capability=%s",
                runtime.provider,
                runtime.model_name,
                base_url,
                runtime.capability or "none",
            )
            return LLMFactory._attach_model_name(model, runtime.model_name)
        if runtime.provider == ModelProvider.CODEX.value:
            raise NotImplementedError("Codex provider routing is reserved but not implemented yet")
        logger.warning("provider_unknown provider=%s fallback=test", runtime.provider)
        return LLMFactory._attach_model_name(TestModel(), "test-model")


__all__ = ["AsyncOpenAI", "LLMFactory", "ModelProvider", "OpenAIChatModel", "OpenAIProvider", "TestModel"]
