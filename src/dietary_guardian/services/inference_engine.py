import time
from dataclasses import dataclass
from typing import Protocol, cast

from pydantic import BaseModel
from pydantic_ai import Agent

from dietary_guardian.agents.provider_factory import LLMFactory, ModelProvider, ModelType
from dietary_guardian.config.settings import get_settings
from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.inference import (
    InferenceHealth,
    InferenceModality,
    ModalityCapabilityProfile,
    InferenceRequest,
    InferenceResponse,
    ProviderMetadata,
)

logger = get_logger(__name__)


class ProviderStrategy(Protocol):
    provider_name: str

    def supports(self, modality: InferenceModality) -> bool: ...

    async def run(self, request: InferenceRequest) -> InferenceResponse: ...

    def health(self) -> InferenceHealth: ...


@dataclass
class _BaseStrategy:
    provider_name: str
    model: ModelType

    def supports(self, modality: InferenceModality) -> bool:
        if self.provider_name == ModelProvider.TEST.value and modality in {
            InferenceModality.IMAGE,
            InferenceModality.MIXED,
        }:
            return False
        return True

    def _provider_metadata(self) -> ProviderMetadata:
        destination = LLMFactory.describe_model_destination(self.model)
        model_name = getattr(self.model, "model_name", getattr(self.model, "model", "unknown"))
        endpoint = "default"
        if "endpoint=" in destination:
            endpoint = destination.split("endpoint=", maxsplit=1)[-1]
        return ProviderMetadata(provider=self.provider_name, model=str(model_name), endpoint=endpoint)

    def _output_retry_budget(self) -> int:
        settings = get_settings()
        if self.provider_name in {ModelProvider.GEMINI.value, ModelProvider.OPENAI.value}:
            return settings.cloud_output_validation_retries
        if self.provider_name in {ModelProvider.OLLAMA.value, ModelProvider.VLLM.value}:
            return settings.local_output_validation_retries
        return 0

    async def run(self, request: InferenceRequest) -> InferenceResponse:
        started = time.perf_counter()
        output_schema = request.output_schema
        output_retries = self._output_retry_budget()
        agent = Agent(
            self.model,
            output_type=output_schema,
            system_prompt=request.system_prompt,
            output_retries=output_retries,
        )
        prompt = request.payload.get("prompt", "")
        logger.info(
            "inference_run_start request_id=%s provider=%s model=%s endpoint=%s modality=%s output_retries=%s",
            request.request_id,
            self.provider_name,
            self._provider_metadata().model,
            self._provider_metadata().endpoint,
            request.modality,
            output_retries,
        )
        try:
            result = await agent.run(prompt)
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - started) * 1000.0
            msg = str(exc)
            if "Exceeded maximum retries" in msg and "output validation" in msg.lower():
                logger.warning(
                    "inference_output_validation_retry_exhausted request_id=%s provider=%s model=%s endpoint=%s output_retries=%s estimated_model_requests=%s latency_ms=%.2f error=%s",
                    request.request_id,
                    self.provider_name,
                    self._provider_metadata().model,
                    self._provider_metadata().endpoint,
                    output_retries,
                    output_retries + 1,
                    latency_ms,
                    msg,
                )
            else:
                logger.exception(
                    "inference_run_failed request_id=%s provider=%s model=%s endpoint=%s latency_ms=%.2f error=%s",
                    request.request_id,
                    self.provider_name,
                    self._provider_metadata().model,
                    self._provider_metadata().endpoint,
                    latency_ms,
                    msg,
                )
            raise
        if not isinstance(result.output, output_schema):
            raise TypeError("Inference output does not match requested schema")
        latency_ms = (time.perf_counter() - started) * 1000.0
        logger.info(
            "inference_strategy_run request_id=%s provider=%s model=%s endpoint=%s modality=%s latency_ms=%.2f",
            request.request_id,
            self.provider_name,
            self._provider_metadata().model,
            self._provider_metadata().endpoint,
            request.modality,
            latency_ms,
        )
        confidence = None
        if hasattr(result.output, "confidence_score"):
            confidence = cast(float | None, getattr(result.output, "confidence_score"))
        return InferenceResponse(
            request_id=request.request_id,
            structured_output=cast(BaseModel, result.output),
            confidence=confidence,
            latency_ms=latency_ms,
            provider_metadata=self._provider_metadata(),
            raw_reference=destination_ref(self.model),
        )

    def health(self) -> InferenceHealth:
        metadata = self._provider_metadata()
        return InferenceHealth(
            provider=metadata.provider,
            model=metadata.model,
            endpoint=metadata.endpoint,
            supports_modalities=[
                InferenceModality.TEXT,
                InferenceModality.IMAGE,
                InferenceModality.MIXED,
            ]
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

    pass


class InferenceEngine:
    def __init__(
        self,
        provider: str | None = None,
        model_name: str | None = None,
        model: ModelType | None = None,
    ) -> None:
        settings = get_settings()
        self.provider = provider or settings.llm_provider
        self.model = model or LLMFactory.get_model(provider=self.provider, model_name=model_name)

        if self.provider in {ModelProvider.GEMINI.value, ModelProvider.OPENAI.value}:
            self.strategy: ProviderStrategy = CloudStrategy(provider_name=self.provider, model=self.model)
        elif self.provider in {ModelProvider.OLLAMA.value, ModelProvider.VLLM.value}:
            self.strategy = LocalStrategy(provider_name=self.provider, model=self.model)
        else:
            self.strategy = TestStrategy(provider_name=ModelProvider.TEST.value, model=self.model)

    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        if not self.strategy.supports(request.modality):
            raise ValueError(f"Provider {self.provider} does not support modality {request.modality}")
        return await self.strategy.run(request)

    def supports(self, modality: InferenceModality) -> bool:
        return self.strategy.supports(modality)

    def health(self) -> InferenceHealth:
        return self.strategy.health()

    def capability_profile(self) -> ModalityCapabilityProfile:
        health = self.health()
        supports = {
            InferenceModality.TEXT: self.supports(InferenceModality.TEXT),
            InferenceModality.IMAGE: self.supports(InferenceModality.IMAGE),
            InferenceModality.MIXED: self.supports(InferenceModality.MIXED),
        }
        expected_latency_ms = {
            InferenceModality.TEXT: 1000 if self.provider in {ModelProvider.GEMINI.value, ModelProvider.OPENAI.value} else 3000,
            InferenceModality.IMAGE: 1500 if self.provider in {ModelProvider.GEMINI.value, ModelProvider.OPENAI.value} else 12000,
            InferenceModality.MIXED: 2000 if self.provider in {ModelProvider.GEMINI.value, ModelProvider.OPENAI.value} else 15000,
        }
        return ModalityCapabilityProfile(
            provider=health.provider,
            model=health.model,
            endpoint=health.endpoint,
            supports=supports,
            expected_latency_ms=expected_latency_ms,
        )


def destination_ref(model: ModelType) -> str:
    return LLMFactory.describe_model_destination(model)
