"""
Build structured log payloads for meal analysis events.

This module centralizes how meal analysis metadata is normalized for logging,
ensuring consistent field names across the pipeline.
"""

from __future__ import annotations

from collections.abc import Iterable

from care_pilot.config.llm import LLMCapability, LLMSettings, ModelProvider
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


def build_meal_analysis_log_payload(
    *,
    user_id: str,
    request_id: str | None,
    correlation_id: str | None,
    provider: str,
    model_name: str | None,
    observation_id: str | None = None,
    meal_id: str | None,
    meal_name: str | None,
    manual_review: bool,
    latency_ms: float | None,
    inference_latency_ms: float | None = None,
    unresolved_count: int,
    risk_tags: Iterable[str] | None = None,
) -> dict[str, object]:
    """Return a normalized logging payload for a meal analysis request."""
    risk_tags_list = list(risk_tags or [])
    return {
        "user_id": user_id,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "provider": provider,
        "model_name": model_name,
        "observation_id": observation_id,
        "meal_id": meal_id,
        "meal_name": meal_name,
        "manual_review": manual_review,
        "latency_ms": latency_ms,
        "inference_latency_ms": inference_latency_ms,
        "unresolved_count": unresolved_count,
        "risk_tag_count": len(risk_tags_list),
    }


def resolve_meal_analysis_model_name(settings: LLMSettings, provider: str | None) -> str | None:
    """Resolve the model name to report for meal analysis logging."""
    capability_target = settings.capability_map.get(LLMCapability.MEAL_VISION)
    if capability_target and capability_target.model:
        return capability_target.model
    if provider:
        try:
            provider_enum = ModelProvider(provider)
        except ValueError:
            provider_enum = settings.provider
    else:
        provider_enum = settings.provider
    if provider_enum == ModelProvider.GEMINI:
        return settings.gemini.model
    if provider_enum == ModelProvider.OPENAI:
        return settings.openai.model
    if provider_enum == ModelProvider.QWEN:
        return settings.qwen.model
    if provider_enum in {ModelProvider.OLLAMA, ModelProvider.VLLM}:
        return settings.local.model
    return None


def log_meal_analysis_event(payload: dict[str, object]) -> None:
    """Log a normalized meal analysis completion event."""
    logger.info(
        "meal_analysis_completed user_id=%s request_id=%s correlation_id=%s provider=%s model_name=%s "
        "observation_id=%s meal_id=%s meal_name=%s manual_review=%s latency_ms=%s inference_latency_ms=%s "
        "unresolved_count=%s risk_tag_count=%s",
        payload.get("user_id"),
        payload.get("request_id"),
        payload.get("correlation_id"),
        payload.get("provider"),
        payload.get("model_name"),
        payload.get("observation_id"),
        payload.get("meal_id"),
        payload.get("meal_name"),
        payload.get("manual_review"),
        payload.get("latency_ms"),
        payload.get("inference_latency_ms"),
        payload.get("unresolved_count"),
        payload.get("risk_tag_count"),
    )
