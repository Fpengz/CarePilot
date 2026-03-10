"""Agent inference execution engine that mediates requests between agents and providers."""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Protocol, cast

from pydantic import BaseModel
from pydantic_ai import Agent

from dietary_guardian.config.app import AppSettings, get_settings
from dietary_guardian.config.llm import LLMCapability, ModelProvider
from dietary_guardian.llm import LLMFactory, ModelType
from dietary_guardian.observability import get_logger
from dietary_guardian.models.inference import (
    InferenceHealth,
    InferenceModality,
    InferenceRequest,
    InferenceResponse,
    ModalityCapabilityProfile,
    ProviderMetadata,
)

logger = get_logger(__name__)


class ProviderStrategy(Protocol):
    capability: str | None
    provider_name: str

    def supports(self, modality: InferenceModality) -> bool: ...
    async def run(self, request: InferenceRequest) -> InferenceResponse: ...
    def health(self) -> InferenceHealth: ...


@dataclass
class _BaseStrategy:
    capability: str | None
    provider_name: str
    model: ModelType

    def supports(self, modality: InferenceModality) -> bool:
        if self.provider_name == ModelProvider.TEST.value and modality in {InferenceModality.IMAGE, InferenceModality.MIXED}:
            return False
        return True

    def _provider_metadata(self) -> ProviderMetadata:
        destination = LLMFactory.describe_model_destination(self.model)
        model_name = getattr(self.model, "model_name", getattr(self.model, "model", "unknown"))
        endpoint = destination.split("endpoint=", maxsplit=1)[-1] if "endpoint=" in destination else "default"
        return ProviderMetadata(
            capability=self.capability,
            provider=self.provider_name,
            model=str(model_name),
            endpoint=endpoint,
        )

    def _output_retry_budget(self) -> int:
        settings = get_settings()
        if self.provider_name in {ModelProvider.GEMINI.value, ModelProvider.OPENAI.value, ModelProvider.CODEX.value}:
            return settings.llm.cloud_output_validation_retries
        if self.provider_name in {ModelProvider.OLLAMA.value, ModelProvider.VLLM.value}:
            return settings.llm.local_output_validation_retries
        return 0

    async def run(self, request: InferenceRequest) -> InferenceResponse:
        started = time.perf_counter()
        output_retries = self._output_retry_budget()
        agent = Agent(
            cast(Any, self.model),
            output_type=request.output_schema,
            system_prompt=request.system_prompt,
            output_retries=output_retries,
        )
        prompt = request.payload.get("prompt", "")
        logger.info(
            "inference_run_start request_id=%s provider=%s model=%s endpoint=%s modality=%s output_retries=%s capability=%s",
            request.request_id,
            self.provider_name,
            self._provider_metadata().model,
            self._provider_metadata().endpoint,
            request.modality,
            output_retries,
            self.capability or "none",
        )
        try:
            result = await agent.run(prompt)
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - started) * 1000.0
            if "Exceeded maximum retries" in str(exc):
                logger.info(
                    "inference_output_validation_retry_exhausted request_id=%s provider=%s estimated_model_requests=%s capability=%s",
                    request.request_id,
                    self.provider_name,
                    max(output_retries + 1, 1),
                    self.capability or "none",
                )
            logger.exception(
                "inference_run_failed request_id=%s provider=%s model=%s endpoint=%s latency_ms=%.2f error=%s capability=%s",
                request.request_id,
                self.provider_name,
                self._provider_metadata().model,
                self._provider_metadata().endpoint,
                latency_ms,
                exc,
                self.capability or "none",
            )
            raise
        if not isinstance(result.output, request.output_schema):
            raise TypeError("Inference output does not match requested schema")
        latency_ms = (time.perf_counter() - started) * 1000.0
        confidence = cast(float | None, getattr(result.output, "confidence_score", None))
        return InferenceResponse(
            request_id=request.request_id,
            structured_output=cast(BaseModel, result.output),
            confidence=confidence,
            latency_ms=latency_ms,
            provider_metadata=self._provider_metadata(),
            raw_reference=LLMFactory.describe_model_destination(self.model),
        )

    def health(self) -> InferenceHealth:
        metadata = self._provider_metadata()
        return InferenceHealth(
            capability=metadata.capability,
            provider=metadata.provider,
            model=metadata.model,
            endpoint=metadata.endpoint,
            supports_modalities=[InferenceModality.TEXT, InferenceModality.IMAGE, InferenceModality.MIXED]
            if self.supports(InferenceModality.IMAGE)
            else [InferenceModality.TEXT],
            healthy=True,
        )


class CloudStrategy(_BaseStrategy):
    pass


class LocalStrategy(_BaseStrategy):
    pass


class TestStrategy(_BaseStrategy):
    def _output_retry_budget(self) -> int:
        return 0


class InferenceEngine:
    def __init__(
        self,
        provider: str | None = None,
        model_name: str | None = None,
        model: ModelType | None = None,
        *,
        settings: AppSettings | None = None,
        capability: LLMCapability | str | None = None,
    ) -> None:
        runtime_settings = settings or get_settings()
        self.capability = capability.value if isinstance(capability, LLMCapability) else capability
        resolved_runtime = LLMFactory._resolve_runtime(
            settings=runtime_settings,
            provider=provider,
            model_name=model_name,
            capability=self.capability,
        )
        self.provider = resolved_runtime.provider
        self.model = model or LLMFactory.get_model(
            provider=provider,
            model_name=model_name,
            settings=runtime_settings,
            capability=self.capability,
        )
        if self.provider in {ModelProvider.GEMINI.value, ModelProvider.OPENAI.value, ModelProvider.CODEX.value}:
            self.strategy: ProviderStrategy = CloudStrategy(self.capability, self.provider, self.model)
        elif self.provider in {ModelProvider.OLLAMA.value, ModelProvider.VLLM.value}:
            self.strategy = LocalStrategy(self.capability, self.provider, self.model)
        else:
            self.strategy = TestStrategy(self.capability, ModelProvider.TEST.value, self.model)

    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        timeout_seconds = get_settings().llm.inference_wall_clock_timeout_seconds
        if not self.strategy.supports(request.modality):
            raise ValueError(f"Provider {self.provider} does not support modality {request.modality}")
        return await asyncio.wait_for(self.strategy.run(request), timeout=timeout_seconds)

    def supports(self, modality: InferenceModality) -> bool:
        return self.strategy.supports(modality)

    def health(self) -> InferenceHealth:
        return self.strategy.health()

    def capability_profile(self) -> ModalityCapabilityProfile:
        health = self.health()
        expected_latency_ms = {
            InferenceModality.TEXT: 1000 if self.provider in {ModelProvider.GEMINI.value, ModelProvider.OPENAI.value} else 3000,
            InferenceModality.IMAGE: 1500 if self.provider in {ModelProvider.GEMINI.value, ModelProvider.OPENAI.value} else 12000,
            InferenceModality.MIXED: 2000 if self.provider in {ModelProvider.GEMINI.value, ModelProvider.OPENAI.value} else 15000,
        }
        return ModalityCapabilityProfile(
            capability=health.capability,
            provider=health.provider,
            model=health.model,
            endpoint=health.endpoint,
            supports={
                InferenceModality.TEXT: self.supports(InferenceModality.TEXT),
                InferenceModality.IMAGE: self.supports(InferenceModality.IMAGE),
                InferenceModality.MIXED: self.supports(InferenceModality.MIXED),
            },
            expected_latency_ms=expected_latency_ms,
        )


def destination_ref(model: ModelType) -> str:
    return LLMFactory.describe_model_destination(model)
