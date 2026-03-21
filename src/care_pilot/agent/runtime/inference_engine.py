"""
Execute agent inference requests through model providers.

This module coordinates inference requests, provider selection, and retries
for agent runtime execution.
"""
import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol, cast

from pydantic import BaseModel, ValidationError
from pydantic_ai import Agent
from pydantic_ai.messages import (
    BinaryImage,
    PartDeltaEvent,
    PartEndEvent,
    TextPart,
    TextPartDelta,
)
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from care_pilot.agent.runtime.inference_types import (
    InferenceHealth,
    InferenceModality,
    InferenceRequest,
    InferenceResponse,
    ModalityCapabilityProfile,
    ProviderMetadata,
)
from care_pilot.agent.runtime.llm_factory import LLMFactory, ModelType
from care_pilot.config.app import AppSettings, get_settings
from care_pilot.config.llm import LLMCapability, ModelProvider
from care_pilot.platform.observability import get_logger
from care_pilot.platform.observability.payloads import pretty_json_payload

logger = get_logger(__name__)
QWEN_PROVIDER = getattr(ModelProvider, "QWEN", ModelProvider.OPENAI)


def _collect_text_from_events(events: list[object]) -> str:
    chunks: list[str] = []
    for event in events:
        if isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
            chunks.append(event.delta.content_delta)
        elif isinstance(event, PartEndEvent) and isinstance(event.part, TextPart):
            chunks.append(event.part.content)
    return "".join(chunks)


def _is_output_validation_failure(exc: Exception) -> bool:
    if isinstance(exc, ValidationError):
        return True
    message = str(exc).lower()
    return "validation" in message and "output" in message


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(?P<body>[\s\S]*?)\s*```", re.IGNORECASE)


def _extract_json_candidates(raw_text: str) -> list[str]:
    candidates: list[str] = []
    for match in _JSON_FENCE_RE.finditer(raw_text):
        body = match.group("body").strip()
        if body:
            candidates.append(body)
    trimmed = raw_text.strip()
    if trimmed:
        candidates.append(trimmed)
    return candidates


def _extract_json_snippets(text: str) -> list[str]:
    snippets: list[str] = []
    if "{" in text and "}" in text:
        start = text.find("{")
        end = text.rfind("}")
        if end > start:
            snippets.append(text[start : end + 1].strip())
    if "[" in text and "]" in text:
        start = text.find("[")
        end = text.rfind("]")
        if end > start:
            snippets.append(text[start : end + 1].strip())
    return snippets


def _coerce_output(schema: type[BaseModel], parsed: object) -> BaseModel | None:
    if isinstance(parsed, dict):
        try:
            return schema.model_validate(parsed)
        except ValidationError:
            return None
    if isinstance(parsed, list) and "instructions" in schema.model_fields:
        payload: dict[str, object] = {"instructions": parsed}
        if "confidence_score" in schema.model_fields:
            payload["confidence_score"] = 0.0
        if "warnings" in schema.model_fields:
            payload["warnings"] = ["Recovered from list output."]
        try:
            return schema.model_validate(payload)
        except ValidationError:
            return None
    return None


def _recover_output_from_text(raw_text: str, schema: type[BaseModel]) -> BaseModel | None:
    for candidate in _extract_json_candidates(raw_text):
        for snippet in _extract_json_snippets(candidate):
            try:
                parsed = json.loads(snippet)
            except json.JSONDecodeError:
                continue
            recovered = _coerce_output(schema, parsed)
            if recovered is not None:
                return recovered
    return None


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
        return not (
            self.provider_name == ModelProvider.TEST.value
            and modality in {InferenceModality.IMAGE, InferenceModality.MIXED}
        )

    def _provider_metadata(self) -> ProviderMetadata:
        destination = LLMFactory.describe_model_destination(self.model)
        model_name = getattr(self.model, "model_name", getattr(self.model, "model", "unknown"))
        endpoint = (
            destination.split("endpoint=", maxsplit=1)[-1]
            if "endpoint=" in destination
            else "default"
        )
        return ProviderMetadata(
            capability=self.capability,
            provider=self.provider_name,
            model=str(model_name),
            endpoint=endpoint,
        )

    def _output_retry_budget(self) -> int:
        settings = get_settings()
        if self.provider_name in {
            ModelProvider.GEMINI.value,
            ModelProvider.OPENAI.value,
            QWEN_PROVIDER.value,
            ModelProvider.CODEX.value,
        }:
            return settings.llm.inference.cloud_output_validation_retries
        if self.provider_name in {
            ModelProvider.OLLAMA.value,
            ModelProvider.VLLM.value,
        }:
            return settings.llm.inference.local_output_validation_retries
        return 0

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
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
        image_bytes = request.payload.get("image_bytes")
        image_mime_type = request.payload.get("image_mime_type") or "image/jpeg"
        settings = get_settings()
        if settings.observability.log_llm_payloads:
            outbound_payload = {
                "request_id": request.request_id,
                "provider": self.provider_name,
                "model": self._provider_metadata().model,
                "endpoint": self._provider_metadata().endpoint,
                "capability": self.capability or "none",
                "modality": request.modality,
                "system_prompt": request.system_prompt,
                "payload": {
                    "prompt": request.payload.get("prompt"),
                    "image_mime_type": image_mime_type,
                    "image_bytes_len": len(image_bytes) if image_bytes else 0,
                    "payload_keys": sorted(request.payload.keys()),
                },
            }
            logger.info("llm_api_outbound payload=%s", pretty_json_payload(outbound_payload))
        logger.debug(
            "inference_engine_payload modality=%s mime_type=%s image_bytes=%s payload_keys=%s",
            request.modality,
            image_mime_type,
            len(image_bytes) if image_bytes else 0,
            sorted(request.payload.keys()),
        )
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
        raw_chunks: list[str] = []

        async def _event_stream_handler(_ctx, events):  # noqa: ANN001
            async for event in events:
                raw = _collect_text_from_events([event])
                if raw:
                    raw_chunks.append(raw)

        try:
            if (
                request.modality in {InferenceModality.IMAGE, InferenceModality.MIXED}
                and image_bytes
            ):
                result = await agent.run(
                    [
                        prompt,
                        BinaryImage(image_bytes, media_type=image_mime_type),
                    ],
                    event_stream_handler=_event_stream_handler,
                )
            else:
                result = await agent.run(prompt, event_stream_handler=_event_stream_handler)
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - started) * 1000.0
            raw_text = "".join(raw_chunks) if raw_chunks else ""
            raw_preview = raw_text[-1200:] if raw_text else None
            if raw_text and _is_output_validation_failure(exc):
                recovered = _recover_output_from_text(raw_text, request.output_schema)
                if recovered is not None:
                    logger.info(
                        "inference_output_recovered request_id=%s provider=%s model=%s endpoint=%s latency_ms=%.2f capability=%s",
                        request.request_id,
                        self.provider_name,
                        self._provider_metadata().model,
                        self._provider_metadata().endpoint,
                        latency_ms,
                        self.capability or "none",
                    )
                    confidence = cast(
                        float | None,
                        getattr(recovered, "confidence_score", None),
                    )
                    return InferenceResponse(
                        request_id=request.request_id,
                        structured_output=recovered,
                        confidence=confidence,
                        latency_ms=latency_ms,
                        provider_metadata=self._provider_metadata(),
                        warnings=["Output validation failed; recovered JSON output."],
                        raw_reference=LLMFactory.describe_model_destination(self.model),
                    )
            if "Exceeded maximum retries" in str(exc):
                logger.info(
                    "inference_output_validation_retry_exhausted request_id=%s provider=%s estimated_model_requests=%s capability=%s",
                    request.request_id,
                    self.provider_name,
                    max(output_retries + 1, 1),
                    self.capability or "none",
                )
            if raw_preview:
                logger.debug("inference_engine_raw_response_preview=%s", raw_preview)
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
        if settings.observability.log_llm_payloads:
            inbound_payload = {
                "request_id": request.request_id,
                "provider": self.provider_name,
                "model": self._provider_metadata().model,
                "endpoint": self._provider_metadata().endpoint,
                "latency_ms": latency_ms,
                "structured_output": result.output.model_dump(mode="json"),
            }
            logger.info("llm_api_inbound payload=%s", pretty_json_payload(inbound_payload))
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
            supports_modalities=(
                [
                    InferenceModality.TEXT,
                    InferenceModality.IMAGE,
                    InferenceModality.MIXED,
                ]
                if self.supports(InferenceModality.IMAGE)
                else [InferenceModality.TEXT]
            ),
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
        if self.provider in {
            ModelProvider.GEMINI.value,
            ModelProvider.OPENAI.value,
            QWEN_PROVIDER.value,
            ModelProvider.CODEX.value,
        }:
            self.strategy: ProviderStrategy = CloudStrategy(
                self.capability, self.provider, self.model
            )
        elif self.provider in {
            ModelProvider.OLLAMA.value,
            ModelProvider.VLLM.value,
        }:
            self.strategy = LocalStrategy(self.capability, self.provider, self.model)
        else:
            self.strategy = TestStrategy(self.capability, ModelProvider.TEST.value, self.model)

    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        timeout_seconds = get_settings().llm.inference.wall_clock_timeout_seconds
        image_bytes = request.payload.get("image_bytes")
        image_mime_type = request.payload.get("image_mime_type") or "image/jpeg"
        logger.debug(
            "inference_engine_payload modality=%s mime_type=%s image_bytes=%s payload_keys=%s",
            request.modality,
            image_mime_type,
            len(image_bytes) if image_bytes else 0,
            sorted(request.payload.keys()),
        )
        if not self.strategy.supports(request.modality):
            raise ValueError(
                f"Provider {self.provider} does not support modality {request.modality}"
            )
        return await asyncio.wait_for(self.strategy.run(request), timeout=timeout_seconds)

    def supports(self, modality: InferenceModality) -> bool:
        return self.strategy.supports(modality)

    def health(self) -> InferenceHealth:
        return self.strategy.health()

    def capability_profile(self) -> ModalityCapabilityProfile:
        health = self.health()
        expected_latency_ms = {
            InferenceModality.TEXT: (
                1000
                if self.provider
                in {
                    ModelProvider.GEMINI.value,
                    ModelProvider.OPENAI.value,
                    QWEN_PROVIDER.value,
                }
                else 3000
            ),
            InferenceModality.IMAGE: (
                1500
                if self.provider
                in {
                    ModelProvider.GEMINI.value,
                    ModelProvider.OPENAI.value,
                    QWEN_PROVIDER.value,
                }
                else 12000
            ),
            InferenceModality.MIXED: (
                2000
                if self.provider
                in {
                    ModelProvider.GEMINI.value,
                    ModelProvider.OPENAI.value,
                    QWEN_PROVIDER.value,
                }
                else 15000
            ),
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
