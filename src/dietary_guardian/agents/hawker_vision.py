import re
import time
from typing import Any, cast
from uuid import uuid4

from pydantic_ai import Agent

from dietary_guardian.agents.provider_factory import LLMFactory, ModelProvider
from dietary_guardian.application.meals import build_meal_record, normalize_vision_result
from dietary_guardian.config.runtime import LocalModelProfile
from dietary_guardian.config.settings import get_settings
from dietary_guardian.domain.meals import MealPerception, MealPortionEstimate, PerceivedMealItem
from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.canonical_food import CanonicalFoodRecord
from dietary_guardian.models.inference import InferenceModality, InferenceRequest
from dietary_guardian.models.meal import (
    GlycemicIndexLevel,
    ImageInput,
    Ingredient,
    MealState,
    Nutrition,
    PortionSize,
    VisionResult,
)
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.services.canonical_food_service import build_default_canonical_food_records, find_food_by_name
from dietary_guardian.services.inference_engine import InferenceEngine

logger = get_logger(__name__)
SLOW_INFERENCE_WARNING_MS = 10_000.0


class _SeededFoodStore:
    def __init__(self) -> None:
        self._records = build_default_canonical_food_records()

    def find_food_by_name(self, *, locale: str, name: str) -> CanonicalFoodRecord | None:
        return find_food_by_name(self._records, name, locale=locale)


class _LazyMealPerceptionAgent:
    def __init__(self, model: Any, system_prompt: str) -> None:
        self._model = model
        self._system_prompt = system_prompt
        self._agent: Agent | None = None

    def _get_agent(self) -> Agent:
        if self._agent is None:
            settings = get_settings()
            provider_name = getattr(getattr(self._model, "provider", None), "__class__", type(None)).__name__.lower()
            local_like = "ollama" in provider_name or "openai" in provider_name
            output_retries = settings.local_output_validation_retries if local_like else settings.cloud_output_validation_retries
            self._agent = Agent(
                self._model,
                output_type=MealPerception,
                system_prompt=self._system_prompt,
                output_retries=output_retries,
            )
        return self._agent

    async def run(self, prompt: str):
        return await self._get_agent().run(prompt)


class HawkerVisionModule:
    def __init__(
        self,
        provider: str | None = None,
        model_name: str | None = None,
        local_profile: LocalModelProfile | None = None,
        food_store: Any | None = None,
    ):
        self.provider = provider or get_settings().llm_provider
        self.food_store = food_store or _SeededFoodStore()
        if local_profile is not None:
            self.model = LLMFactory.from_profile(local_profile)
            self.provider = local_profile.provider
        else:
            self.model = LLMFactory.get_model(self.provider, model_name)
        engine_model_name = getattr(self.model, "model_name", None)
        self.inference_engine = InferenceEngine(
            provider=self.provider,
            model_name=engine_model_name,
            model=self.model,
        )
        self.system_prompt = (
            "You are the 'Hawker Vision' Expert, a specialized AI for Singaporean cuisine. "
            "Your role is perception only. Return strict JSON matching the MealPerception schema. "
            "Detect likely foods, component count, candidate aliases, coarse portion estimates, visible preparation cues, image quality, confidence, and uncertainty. "
            "Do not estimate nutrition, do not produce risk tags, and do not give advice."
        )
        self.agent = _LazyMealPerceptionAgent(self.model, self.system_prompt)
        logger.info(
            "hawker_vision_model_destination %s",
            LLMFactory.describe_model_destination(self.model),
        )

    def _endpoint(self) -> str:
        provider_obj = getattr(self.model, "provider", getattr(self.model, "_provider", None))
        return cast(str, getattr(provider_obj, "base_url", "default"))

    @staticmethod
    def _format_latency_ms(latency_ms: float) -> str:
        if latency_ms >= 1000.0:
            return f"{latency_ms / 1000.0:.2f}s"
        return f"{latency_ms:.0f}ms"

    def _log_response_summary(
        self,
        *,
        request_id: str,
        correlation_id: str | None,
        user_id: str | None,
        source: str | None,
        filename: str | None,
        result: VisionResult,
        reason: str,
    ) -> None:
        logger.info(
            "hawker_vision_response_summary request_id=%s correlation_id=%s user_id=%s source=%s filename=%s provider=%s model=%s endpoint=%s destination=%s confidence=%.3f manual_review=%s latency_ms=%.2f reason=%s",
            request_id,
            correlation_id,
            user_id,
            source,
            filename,
            self.provider,
            getattr(self.model, "model_name", "unknown"),
            self._endpoint(),
            LLMFactory.describe_model_destination(self.model),
            result.primary_state.confidence_score,
            result.needs_manual_review,
            result.processing_latency_ms,
            reason,
        )

    def _build_clarification_response(
        self,
        reason: str,
        confidence_score: float = 0.0,
        source: str | None = None,
        filename: str | None = None,
        latency_ms: float = 0.0,
    ) -> VisionResult:
        detail_parts: list[str] = []
        if source:
            detail_parts.append(f"Source: {source}")
        if filename:
            detail_parts.append(f"Filename: {filename}")
        details = " | ".join(detail_parts)
        message = f"{reason}. {details}".strip()
        state = MealState(
            dish_name="Clarification Required",
            confidence_score=confidence_score,
            identification_method="User_Manual",
            ingredients=[],
            nutrition=Nutrition(calories=0, carbs_g=0, sugar_g=0, protein_g=0, fat_g=0, sodium_mg=0),
            visual_anomalies=["Image uncertainty"],
            suggested_modifications=[
                "Clarification needed: please retake the photo with better lighting.",
                "Clarification needed: capture the whole dish from top-down angle.",
            ],
        )
        return VisionResult(
            primary_state=state,
            perception=MealPerception(
                meal_detected=False,
                items=[],
                uncertainties=[reason],
                image_quality="poor",
                confidence_score=confidence_score,
            ),
            raw_ai_output=message,
            needs_manual_review=True,
            processing_latency_ms=latency_ms,
            model_version=getattr(self.model, "model_name", "unknown"),
        )

    def _build_prompt(self, image_input: Any) -> tuple[str, str | None, str | None]:
        prompt = "Analyze the provided input and generate a MealPerception."
        if isinstance(image_input, str):
            return f"{prompt} Context: {image_input}", None, None
        if isinstance(image_input, ImageInput):
            context = (
                f"Image metadata: source={image_input.source}, "
                f"filename={image_input.filename}, mime_type={image_input.mime_type}, "
                f"bytes={len(image_input.content)}"
            )
            return f"{prompt} {context}", image_input.source, image_input.filename
        return prompt, None, None

    def _perception_to_meal_state(self, perception: MealPerception) -> MealState:
        primary_item = perception.items[0] if perception.items else None
        dish_name = primary_item.label if primary_item is not None else "Unidentified meal"
        amount = primary_item.portion_estimate.amount if primary_item is not None else 1.0
        if amount <= 0.75:
            portion_size = PortionSize.SMALL
        elif amount >= 1.5:
            portion_size = PortionSize.LARGE
        else:
            portion_size = PortionSize.STANDARD
        return MealState(
            dish_name=dish_name,
            confidence_score=perception.confidence_score,
            identification_method="AI_Flash",
            ingredients=[Ingredient(name=item.label) for item in perception.items[:8]],
            nutrition=Nutrition(calories=0, carbs_g=0, sugar_g=0, protein_g=0, fat_g=0, sodium_mg=0),
            portion_size=portion_size,
            glycemic_index_estimate=GlycemicIndexLevel.UNKNOWN,
            visual_anomalies=list(perception.uncertainties),
        )

    def _test_perception(self, image_input: Any) -> MealPerception:
        tokens: list[str]
        if isinstance(image_input, str):
            tokens = [token for token in re.split(r"[^a-zA-Z0-9]+", image_input) if token]
        else:
            filename = getattr(image_input, "filename", "") or ""
            tokens = [
                token
                for token in re.split(r"[^a-zA-Z0-9]+", filename)
                if token and token.lower() not in {"jpg", "jpeg", "png", "heic"}
            ]
        filtered = [token.replace("-", " ") for token in tokens if len(token) > 2]
        labels = filtered[:3] or ["laksa"]
        items = [
            PerceivedMealItem(
                label=label,
                candidate_aliases=[label],
                portion_estimate=MealPortionEstimate(amount=1.0, unit="serving", confidence=0.8),
                preparation="observed",
                confidence=max(0.6, 0.9 - index * 0.1),
            )
            for index, label in enumerate(labels)
        ]
        image_quality = "fair" if len(items) > 1 else "good"
        confidence = 0.72 if len(items) > 1 else 0.9
        return MealPerception(
            meal_detected=True,
            items=items,
            uncertainties=["Multiple visible components may need deterministic normalization."] if len(items) > 1 else [],
            image_quality=image_quality,
            confidence_score=confidence,
        )

    async def analyze_dish(
        self,
        image_input: Any,
        user_id: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
    ) -> VisionResult:
        started = time.perf_counter()
        request_id = request_id or str(uuid4())
        try:
            prompt, source, filename = self._build_prompt(image_input)
            logger.info(
                "hawker_vision_analyze_start request_id=%s user_id=%s source=%s filename=%s provider=%s model=%s endpoint=%s destination=%s",
                request_id,
                user_id,
                source,
                filename,
                self.provider,
                getattr(self.model, "model_name", "unknown"),
                self._endpoint(),
                LLMFactory.describe_model_destination(self.model),
            )

            requested_modality = InferenceModality.IMAGE if isinstance(image_input, ImageInput) else InferenceModality.TEXT

            if self.provider == ModelProvider.TEST.value:
                perception = self._test_perception(image_input)
            elif requested_modality != InferenceModality.TEXT and not self.inference_engine.supports(requested_modality):
                elapsed = (time.perf_counter() - started) * 1000.0
                clarification = self._build_clarification_response(
                    reason="Selected runtime cannot process raw image bytes in this mode",
                    source=image_input.source,
                    filename=image_input.filename,
                    latency_ms=elapsed,
                )
                self._log_response_summary(
                    request_id=request_id,
                    correlation_id=correlation_id,
                    user_id=user_id,
                    source=image_input.source,
                    filename=image_input.filename,
                    result=clarification,
                    reason="unsupported_modality",
                )
                return clarification

            logger.info(
                "hawker_vision_request request_id=%s correlation_id=%s user_id=%s source=%s filename=%s provider=%s model=%s endpoint=%s inference_engine_v2=%s local_output_retries=%s cloud_output_retries=%s",
                request_id,
                correlation_id,
                user_id,
                source,
                filename,
                self.provider,
                getattr(self.model, "model_name", "unknown"),
                self._endpoint(),
                get_settings().use_inference_engine_v2,
                get_settings().local_output_validation_retries,
                get_settings().cloud_output_validation_retries,
            )

            if self.provider == ModelProvider.TEST.value:
                pass
            elif get_settings().use_inference_engine_v2:
                request = InferenceRequest(
                    request_id=request_id,
                    user_id=user_id,
                    modality=requested_modality,
                    payload={"prompt": prompt},
                    runtime_profile={
                        "provider": self.provider,
                        "model": str(getattr(self.model, "model_name", "unknown")),
                    },
                    trace_context={"source": source or "unknown", "filename": filename or "unknown"},
                    output_schema=MealPerception,
                    system_prompt=self.system_prompt,
                )
                inference = await self.inference_engine.infer(request)
                perception = cast(MealPerception, inference.structured_output)
            else:
                result = await self.agent.run(prompt)
                if not isinstance(result.output, MealPerception):
                    raise TypeError("Model output is not a MealPerception payload.")
                perception = cast(MealPerception, result.output)

            meal_state = self._perception_to_meal_state(perception)
            needs_review = False
            if (not perception.meal_detected) or perception.confidence_score < 0.4:
                elapsed = (time.perf_counter() - started) * 1000.0
                clarification = self._build_clarification_response(
                    reason="Clarification required due to low confidence or image ambiguity",
                    confidence_score=perception.confidence_score,
                    source=source,
                    filename=filename,
                    latency_ms=elapsed,
                )
                self._log_response_summary(
                    request_id=request_id,
                    correlation_id=correlation_id,
                    user_id=user_id,
                    source=source,
                    filename=filename,
                    result=clarification,
                    reason="low_confidence_clarification",
                )
                return clarification

            if perception.confidence_score < 0.75 or perception.image_quality != "good" or len(perception.items) > 1:
                meal_state.suggested_modifications.append("Ask for clarification: request a clearer image or alternate angle.")
                needs_review = True

            elapsed = (time.perf_counter() - started) * 1000.0
            logger.info(
                "hawker_vision_analyze_complete request_id=%s user_id=%s source=%s filename=%s provider=%s model=%s endpoint=%s latency_ms=%.2f latency_human=%s manual_review=%s",
                request_id,
                user_id,
                source,
                filename,
                self.provider,
                getattr(self.model, "model_name", "unknown"),
                self._endpoint(),
                elapsed,
                self._format_latency_ms(elapsed),
                needs_review,
            )
            if elapsed >= SLOW_INFERENCE_WARNING_MS:
                logger.warning(
                    "hawker_vision_slow_inference request_id=%s user_id=%s provider=%s model=%s endpoint=%s latency_ms=%.2f latency_human=%s threshold_ms=%.0f",
                    request_id,
                    user_id,
                    self.provider,
                    getattr(self.model, "model_name", "unknown"),
                    self._endpoint(),
                    elapsed,
                    self._format_latency_ms(elapsed),
                    SLOW_INFERENCE_WARNING_MS,
                )
            response_result = VisionResult(
                primary_state=meal_state,
                perception=perception,
                raw_ai_output=f"Processed via {self.provider}:{getattr(self.model, 'model_name', 'unknown')}",
                needs_manual_review=needs_review,
                processing_latency_ms=elapsed,
                model_version=getattr(self.model, "model_name", "unknown"),
            )
            self._log_response_summary(
                request_id=request_id,
                correlation_id=correlation_id,
                user_id=user_id,
                source=source,
                filename=filename,
                result=response_result,
                reason="inference_complete",
            )
            return response_result

        except Exception as e:
            logger.error(f"Vision Pipeline Failed: {e}")
            elapsed = (time.perf_counter() - started) * 1000.0
            msg = str(e)
            if "Exceeded maximum retries" in msg and "output validation" in msg.lower():
                retry_budget = (
                    get_settings().local_output_validation_retries
                    if self.provider in {ModelProvider.OLLAMA.value, ModelProvider.VLLM.value}
                    else get_settings().cloud_output_validation_retries
                )
                logger.warning(
                    "hawker_vision_output_validation_retry_exhausted request_id=%s correlation_id=%s user_id=%s provider=%s model=%s estimated_model_requests=%s output_retries=%s latency_ms=%.2f",
                    request_id,
                    correlation_id,
                    user_id,
                    self.provider,
                    getattr(self.model, "model_name", "unknown"),
                    retry_budget + 1,
                    retry_budget,
                    elapsed,
                )
            logger.error(
                "hawker_vision_analyze_failed request_id=%s correlation_id=%s user_id=%s provider=%s model=%s endpoint=%s latency_ms=%.2f error=%s",
                request_id,
                correlation_id,
                user_id,
                self.provider,
                getattr(self.model, "model_name", "unknown"),
                self._endpoint(),
                elapsed,
                e,
            )
            clarification = self._build_clarification_response(
                reason=f"Vision pipeline failed: {e}",
                source=getattr(image_input, "source", None),
                filename=getattr(image_input, "filename", None),
                latency_ms=elapsed,
            )
            self._log_response_summary(
                request_id=request_id,
                correlation_id=correlation_id,
                user_id=user_id,
                source=getattr(image_input, "source", None),
                filename=getattr(image_input, "filename", None),
                result=clarification,
                reason="pipeline_exception",
            )
            return clarification

    async def analyze_and_record(
        self,
        image_input: Any,
        user_id: str,
        request_id: str | None = None,
        correlation_id: str | None = None,
    ) -> tuple[VisionResult, MealRecognitionRecord]:
        logger.info(
            "hawker_vision_analyze_and_record_start user_id=%s request_id=%s correlation_id=%s",
            user_id,
            request_id,
            correlation_id,
        )
        result = await self.analyze_dish(
            image_input,
            user_id=user_id,
            request_id=request_id,
            correlation_id=correlation_id,
        )
        result = normalize_vision_result(vision_result=result, food_store=self.food_store)
        record = build_meal_record(
            image_input=image_input,
            user_id=user_id,
            vision_result=result,
            request_id=request_id,
        )
        logger.info(
            "hawker_vision_analyze_and_record_complete user_id=%s record_id=%s multi_item_count=%s",
            user_id,
            record.id,
            record.multi_item_count,
        )
        return result, record
