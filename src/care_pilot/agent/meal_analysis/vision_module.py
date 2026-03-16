"""Meal analysis facade used by API shims and capability tests.

This module provides a small wrapper around the current meal perception agent
and deterministic normalization logic. It is intentionally narrow: it does not
persist durable state and does not orchestrate multi-feature workflows.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from pydantic_ai import Agent
from PIL import Image, UnidentifiedImageError

from care_pilot.agent.runtime.inference_engine import InferenceEngine
from care_pilot.agent.runtime.inference_types import (
    InferenceModality,
    InferenceRequest,
    InferenceResponse,
)
from care_pilot.agent.runtime.llm_factory import LLMFactory
from care_pilot.config.app import get_settings
from care_pilot.config.llm import LLMCapability, LocalModelProfile
from care_pilot.features.meals.domain.models import (
    ImageInput,
    MealPerception,
    VisionResult,
)
from care_pilot.features.meals.domain.normalization import (
    build_clarification_response,
    perception_to_meal_state,
)
from care_pilot.features.meals.domain.recognition import MealRecognitionRecord
from care_pilot.features.meals.domain.normalization import (
    build_meal_record,
    normalize_vision_result,
)
from care_pilot.features.recommendations.domain.canonical_food_matching import (
    build_default_canonical_food_records,
)
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


class _InMemoryCanonicalFoodStore:
    def __init__(self) -> None:
        self._records = build_default_canonical_food_records()

    def list_canonical_foods(self, *, locale: str, limit: int = 500) -> list[Any]:
        items = [
            item
            for item in self._records
            if getattr(item, "locale", None) == locale and getattr(item, "active", True)
        ]
        return items[:limit]

    def find_food_by_name(self, *, locale: str, name: str) -> Any | None:
        target = name.strip().lower()
        if not target:
            return None
        for item in self._records:
            if getattr(item, "locale", None) != locale or not getattr(item, "active", True):
                continue
            title = str(getattr(item, "title", "")).strip().lower()
            if title == target:
                return item
        return None


@dataclass(frozen=True)
class HawkerVisionResult:
    primary_state: Any
    perception: MealPerception | None
    enriched_event: Any | None
    raw_ai_output: str
    needs_manual_review: bool
    processing_latency_ms: float
    model_version: str
    provider: str | None = None

    @classmethod
    def from_vision_result(cls, result: VisionResult) -> HawkerVisionResult:
        return cls(
            primary_state=result.primary_state,
            perception=result.perception,
            enriched_event=result.enriched_event,
            raw_ai_output=result.raw_ai_output,
            needs_manual_review=result.needs_manual_review,
            processing_latency_ms=result.processing_latency_ms,
            model_version=result.model_version,
            provider=result.provider,
        )

    def to_vision_result(self) -> VisionResult:
        return VisionResult(
            primary_state=self.primary_state,
            perception=self.perception,
            enriched_event=self.enriched_event,
            raw_ai_output=self.raw_ai_output,
            needs_manual_review=self.needs_manual_review,
            processing_latency_ms=self.processing_latency_ms,
            model_version=self.model_version,
            provider=self.provider,
        )


SYSTEM_PROMPT = (
    "You are the 'Hawker Vision' Expert, a specialized AI for Singaporean cuisine. "
    "Your role is perception only. Return strict JSON matching the MealPerception schema. "
    "Detect likely foods, component count, candidate aliases, coarse portion estimates, "
    "visible preparation cues, image quality, confidence, and uncertainty. "
    "image_quality must be one of: poor, fair, good, unknown (string only). "
    "items must be an array; do not return an object for items."
)


class HawkerVisionModule:
    """Facade for perception + deterministic normalization helpers."""

    def __init__(
        self,
        *,
        provider: str | None = None,
        local_profile: LocalModelProfile | None = None,
    ) -> None:
        requested_provider = str(provider) if provider is not None else None
        self.requested_provider = requested_provider
        self._food_store = _InMemoryCanonicalFoodStore()

        if local_profile is not None:
            model = LLMFactory.from_profile(local_profile)
            self.inference_engine = InferenceEngine(model=model)
            agent_model = model
        else:
            self.inference_engine = InferenceEngine(provider=requested_provider)
            agent_model = LLMFactory.get_model(
                provider=requested_provider,
                capability=LLMCapability.MEAL_VISION,
            )

        self.provider = getattr(self.inference_engine, "provider", requested_provider) or "unknown"

        try:
            self.agent = cast(
                Any,
                Agent(
                    cast(Any, agent_model),
                    output_type=MealPerception,
                    system_prompt=SYSTEM_PROMPT,
                ),
            )
        except Exception:  # noqa: BLE001
            self.agent = cast(
                Any,
                Agent(
                    "test",
                    output_type=MealPerception,
                    system_prompt=SYSTEM_PROMPT,
                ),
            )

    def _use_inference_engine_v2(self) -> bool:
        return bool(get_settings().llm.inference.use_engine_v2)

    def _build_prompt(
        self, dish: str | ImageInput
    ) -> tuple[str, InferenceModality, bytes | None, str | None]:
        if isinstance(dish, ImageInput):
            label_hint = Path(dish.filename or "meal").stem or "meal"
            prompt = f"Identify the meal in this image. Filename hint: {label_hint}."
            image_bytes = dish.content
            image_mime_type = dish.mime_type
            if dish.mime_type == "image/webp":
                try:
                    with Image.open(BytesIO(dish.content)) as img:
                        converted = img.convert("RGB")
                        buffer = BytesIO()
                        converted.save(buffer, format="JPEG")
                        image_bytes = buffer.getvalue()
                        image_mime_type = "image/jpeg"
                except (
                    UnidentifiedImageError,
                    OSError,
                    ValueError,
                ):  # noqa: BLE001
                    logger.info(
                        "hawker_vision_webp_conversion_failed filename=%s",
                        dish.filename,
                    )
            return (
                prompt,
                InferenceModality.IMAGE,
                image_bytes,
                image_mime_type,
            )
        return (
            f"Identify the meal described here: {dish}",
            InferenceModality.TEXT,
            None,
            None,
        )

    def _stub_test_perception(self, dish: str | ImageInput) -> MealPerception:
        if isinstance(dish, ImageInput):
            stem = Path(dish.filename or "hawker").stem or "hawker"
            count = 1
            raw = dish.metadata.get("multi_item_count")
            if raw:
                try:
                    count = max(1, int(raw))
                except ValueError:
                    count = 1
            items = [
                {
                    "label": stem if idx == 0 else f"{stem}_{idx + 1}",
                    "candidate_aliases": [stem],
                    "portion_estimate": {
                        "amount": 1.0,
                        "unit": "serving",
                        "confidence": 0.9,
                    },
                    "preparation": "unknown",
                    "confidence": 0.9 if count == 1 else 0.7,
                }
                for idx in range(count)
            ]
            return MealPerception.model_validate(
                {
                    "meal_detected": True,
                    "items": items,
                    "uncertainties": [],
                    "image_quality": "good",
                    "confidence_score": 0.95 if count == 1 else 0.72,
                }
            )
        lowered = dish.lower()
        label = "Laksa" if "laksa" in lowered else "Mee Rebus" if "mee" in lowered else "Meal"
        return MealPerception.model_validate(
            {
                "meal_detected": True,
                "items": [
                    {
                        "label": label,
                        "candidate_aliases": [label],
                        "portion_estimate": {
                            "amount": 1.0,
                            "unit": "bowl",
                            "confidence": 0.9,
                        },
                        "preparation": "soup" if "laksa" in lowered else None,
                        "confidence": 0.92,
                    }
                ],
                "uncertainties": [],
                "image_quality": "good",
                "confidence_score": 0.92,
            }
        )

    async def analyze_dish(self, dish: str | ImageInput) -> VisionResult:
        prompt, modality, image_bytes, image_mime_type = self._build_prompt(dish)
        logger.debug(
            "hawker_vision_inference_payload modality=%s mime_type=%s image_bytes=%s prompt_preview=%s",
            modality,
            image_mime_type,
            len(image_bytes) if image_bytes else 0,
            prompt[:120],
        )

        if self.provider == "test":
            perception = self._stub_test_perception(dish)
            meal_state = perception_to_meal_state(perception)
            needs_review = (
                len(perception.items) > 1
                or perception.confidence_score < 0.75
                or perception.image_quality != "good"
            )
            destination = "unknown"
            try:
                destination = LLMFactory.describe_model_destination(
                    getattr(self.inference_engine, "model")
                )
            except Exception:  # noqa: BLE001
                destination = "unknown"
            logger.info(
                "hawker_vision_response_summary provider=%s destination=%s confidence=%.2f items=%s latency_ms=%.2f",
                self.provider,
                destination,
                perception.confidence_score,
                len(perception.items),
                0.0,
            )
            return VisionResult(
                primary_state=meal_state,
                perception=perception,
                enriched_event=None,
                raw_ai_output="test-stub",
                needs_manual_review=needs_review,
                processing_latency_ms=0.0,
                model_version="test",
                provider=self.provider,
            )

        perception: MealPerception
        raw: str
        latency_ms = 0.0
        model_version = "unknown"

        if self._use_inference_engine_v2():
            request = InferenceRequest(
                request_id=str(uuid4()),
                user_id=None,
                modality=modality,
                payload={
                    "prompt": prompt,
                    "image_bytes": image_bytes,
                    "image_mime_type": image_mime_type,
                },
                output_schema=MealPerception,
                system_prompt=SYSTEM_PROMPT,
            )
            response = cast(InferenceResponse, await self.inference_engine.infer(request))
            perception = cast(MealPerception, response.structured_output)
            raw = response.structured_output.model_dump_json()
            latency_ms = response.latency_ms
            model_version = response.provider_metadata.model
        else:
            if modality == InferenceModality.IMAGE and image_bytes is not None:
                from pydantic_ai.messages import BinaryImage

                result = await self.agent.run(
                    [
                        prompt,
                        BinaryImage(
                            image_bytes,
                            media_type=image_mime_type or "image/jpeg",
                        ),
                    ]
                )
            else:
                result = await self.agent.run(prompt)
            perception = cast(MealPerception, getattr(result, "output"))
            raw = perception.model_dump_json()

        destination = "unknown"
        try:
            destination = LLMFactory.describe_model_destination(
                getattr(self.inference_engine, "model")
            )
        except Exception:  # noqa: BLE001
            destination = "unknown"
        logger.info(
            "hawker_vision_response_summary provider=%s destination=%s confidence=%.2f items=%s latency_ms=%.2f",
            self.provider,
            destination,
            perception.confidence_score,
            len(perception.items),
            latency_ms,
        )

        if not perception.meal_detected or perception.confidence_score < 0.4:
            return build_clarification_response(
                reason="Clarification required due to low confidence",
                confidence_score=perception.confidence_score,
                latency_ms=latency_ms,
                model_version=model_version,
            ).model_copy(update={"perception": perception, "provider": self.provider})

        meal_state = perception_to_meal_state(perception)
        needs_review = (
            perception.confidence_score < 0.75
            or perception.image_quality != "good"
            or len(perception.items) > 1
        )
        return VisionResult(
            primary_state=meal_state,
            perception=perception,
            enriched_event=None,
            raw_ai_output=raw,
            needs_manual_review=needs_review,
            processing_latency_ms=latency_ms,
            model_version=model_version,
            provider=self.provider,
        )

    async def analyze_and_record(
        self,
        image_input: ImageInput,
        *,
        user_id: str,
        locale: str = "en-SG",
    ) -> tuple[VisionResult, MealRecognitionRecord]:
        vision_result = await self.analyze_dish(image_input)
        normalized = normalize_vision_result(
            vision_result=vision_result,
            food_store=self._food_store,
            locale=locale,
        )
        record = build_meal_record(
            image_input=image_input, user_id=user_id, vision_result=normalized
        )
        return normalized, record


__all__ = ["HawkerVisionModule", "HawkerVisionResult"]
