"""
Resolve model runtimes based on capability routing.

This module maps capability requests to concrete LLM runtime targets using
configuration profiles.
"""

import os

from care_pilot.agent.runtime.llm_types import ResolvedModelRuntime
from care_pilot.config.app import AppSettings
from care_pilot.config.llm import LLMCapability, LLMCapabilityTarget, ModelProvider


class LLMCapabilityRouter:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    def resolve(self, capability: LLMCapability | str | None) -> ResolvedModelRuntime | None:
        if capability is None:
            return None

        capability_name = capability.value if isinstance(capability, LLMCapability) else capability
        targets = self._settings.llm.capability_map
        # Coerce the string key to LLMCapability for typed dict lookup; unknown keys get None.
        try:
            cap_key = LLMCapability(capability_name)
        except ValueError:
            cap_key = None
        target = (targets.get(cap_key) if cap_key is not None else None) or targets.get(
            LLMCapability.FALLBACK
        )
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
            return self._settings.llm.gemini.model
        if target.provider == ModelProvider.OPENAI.value:
            return self._settings.llm.openai.model
        if target.provider == ModelProvider.QWEN.value:
            return self._settings.llm.qwen.model
        return self._settings.llm.local.model

    def _resolve_base_url(self, provider: str, target: LLMCapabilityTarget) -> str | None:
        if target.base_url is not None:
            return str(target.base_url)
        if provider == ModelProvider.OPENAI.value:
            return self._settings.llm.openai.base_url
        if provider == ModelProvider.QWEN.value:
            return self._settings.llm.qwen.base_url
        if provider in {ModelProvider.OLLAMA.value, ModelProvider.VLLM.value}:
            return self._settings.llm.local.base_url
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
            return self._settings.llm.openai.api_key
        if provider == ModelProvider.QWEN.value:
            return self._settings.llm.qwen.api_key
        if provider in {ModelProvider.OLLAMA.value, ModelProvider.VLLM.value}:
            return self._settings.llm.local.api_key
        return None
