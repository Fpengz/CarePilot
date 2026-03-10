"""Capability-aware routing from settings to resolved LLM runtime targets."""

import os

from dietary_guardian.config.app import AppSettings
from dietary_guardian.config.llm import LLMCapability, LLMCapabilityTarget, ModelProvider
from dietary_guardian.llm.types import ResolvedModelRuntime


class LLMCapabilityRouter:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    def resolve(self, capability: LLMCapability | str | None) -> ResolvedModelRuntime | None:
        if capability is None:
            return None

        capability_name = capability.value if isinstance(capability, LLMCapability) else capability
        targets = self._settings.llm.capability_targets
        target = targets.get(capability_name) or targets.get(LLMCapability.FALLBACK.value)
        if target is None:
            return None

        provider = target.provider
        return ResolvedModelRuntime(
            provider=provider,
            model_name=self._resolve_model_name(target),
            capability=capability_name,
            base_url=self._resolve_base_url(provider, target),
            api_key=self._resolve_api_key(provider, target),
        )

    def _resolve_model_name(self, target: LLMCapabilityTarget) -> str:
        if target.model:
            return target.model
        if target.provider == ModelProvider.GEMINI.value:
            return self._settings.llm.gemini_model
        if target.provider == ModelProvider.OPENAI.value:
            return self._settings.llm.openai_model
        return self._settings.llm.local_llm_model

    def _resolve_base_url(self, provider: str, target: LLMCapabilityTarget) -> str | None:
        if target.base_url is not None:
            return str(target.base_url)
        if provider == ModelProvider.OPENAI.value:
            return str(self._settings.llm.openai_base_url) if self._settings.llm.openai_base_url else None
        if provider in {ModelProvider.OLLAMA.value, ModelProvider.VLLM.value}:
            return str(self._settings.llm.local_llm_base_url) if self._settings.llm.local_llm_base_url else None
        return None

    def _resolve_api_key(self, provider: str, target: LLMCapabilityTarget) -> str | None:
        if target.api_key:
            return target.api_key
        if target.api_key_env:
            env_value = os.getenv(target.api_key_env)
            if env_value:
                return env_value
        if provider == ModelProvider.GEMINI.value:
            return self._settings.llm.effective_google_api_key
        if provider == ModelProvider.OPENAI.value:
            return self._settings.llm.openai_api_key
        if provider in {ModelProvider.OLLAMA.value, ModelProvider.VLLM.value}:
            return self._settings.llm.local_llm_api_key
        return None
