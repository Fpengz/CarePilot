import re
import time
from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4
from pydantic_ai import Agent
from dietary_guardian.models.meal import (
    ImageInput,
    MealState,
    VisionResult,
    GlycemicIndexLevel,
    Ingredient,
    Nutrition,
)
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.agents.provider_factory import LLMFactory, ModelProvider
from dietary_guardian.config.runtime import LocalModelProfile
from dietary_guardian.config.settings import get_settings
from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.inference import InferenceModality, InferenceRequest
from dietary_guardian.services.inference_engine import InferenceEngine

# Configure logging
logger = get_logger(__name__)
SLOW_INFERENCE_WARNING_MS = 10_000.0

# --- Mock Database for Fallback (SG-FoodID) ---
# In production, this would be a SQLite/Vector DB lookup
HPB_DATABASE: dict[str, dict[str, Any]] = {
    "Mee Rebus": {
        "calories": 571,
        "sodium_mg": 2160,
        "carbs_g": 82,
        "protein_g": 23,
        "fat_g": 18,
        "sugar_g": 14,
        "fiber_g": 6,
        "glycemic_index": GlycemicIndexLevel.MEDIUM,
        "ingredients": ["Yellow Noodles", "Tau Pok", "Hard Boiled Egg", "Bean Sprouts"],
        "local_variant": "Malay Style"
    },
    "Mee Siam": {
        "calories": 520,
        "sodium_mg": 2660,
        "carbs_g": 76,
        "protein_g": 21,
        "fat_g": 16,
        "sugar_g": 9,
        "fiber_g": 5,
        "glycemic_index": GlycemicIndexLevel.MEDIUM,
        "ingredients": ["Bee Hoon", "Tau Pok", "Egg", "Chives"],
        "local_variant": "Nyonya/Malay Style"
    },
    "Laksa": {
        "calories": 591,
        "sodium_mg": 1580,
        "carbs_g": 59,
        "protein_g": 22,
        "fat_g": 31,
        "sugar_g": 5,
        "fiber_g": 4,
        "glycemic_index": GlycemicIndexLevel.HIGH,
        "ingredients": ["Thick Bee Hoon", "Cockles", "Prawns", "Fish Cake", "Coconut Milk"],
        "local_variant": "Katong Style"
    },
    "Char Kway Teow": {
        "calories": 744,
        "sodium_mg": 1450,
        "carbs_g": 76,
        "protein_g": 23,
        "fat_g": 38,
        "sugar_g": 6,
        "fiber_g": 4,
        "glycemic_index": GlycemicIndexLevel.HIGH,
        "ingredients": ["Kway Teow", "Yellow Noodles", "Cockles", "Lup Cheong", "Egg", "Lard"],
        "local_variant": "Singapore Style"
    }
}


class _LazyMealStateAgent:
    def __init__(self, model: Any, system_prompt: str) -> None:
        self._model = model
        self._system_prompt = system_prompt
        self._agent: Agent | None = None

    def _get_agent(self) -> Agent:
        if self._agent is None:
            settings = get_settings()
            provider_name = getattr(getattr(self._model, "provider", None), "__class__", type(None)).__name__.lower()
            local_like = "ollama" in provider_name or "openai" in provider_name
            output_retries = (
                settings.local_output_validation_retries if local_like else settings.cloud_output_validation_retries
            )
            self._agent = Agent(
                self._model,
                output_type=MealState,
                system_prompt=self._system_prompt,
                output_retries=output_retries,
            )
        return self._agent

    async def run(self, prompt: str):
        return await self._get_agent().run(prompt)

class HawkerVisionModule:
    def __init__(
        self,
        provider: str = ModelProvider.GEMINI,
        model_name: str | None = None,
        local_profile: LocalModelProfile | None = None,
    ):
        self.provider = provider
        if local_profile is not None:
            self.model = LLMFactory.from_profile(local_profile)
            self.provider = local_profile.provider
        else:
            self.model = LLMFactory.get_model(provider, model_name)
        engine_model_name = getattr(self.model, "model_name", None)
        self.inference_engine = InferenceEngine(
            provider=self.provider,
            model_name=engine_model_name,
            model=self.model,
        )
        
        # System Prompt aligned with GEMINI.md
        system_prompt = (
            "You are the 'Hawker Vision' Expert, a specialized AI for Singaporean cuisine. "
            "Your task is to identify hawker dishes from images with high precision. "
            "1. LOCALIZATION: Distinguish between visually similar dishes (e.g., Mee Rebus vs Mee Siam). "
            "   - Look for gravy viscosity, noodle type (yellow vs vermicelli), and specific toppings. "
            "   - Identify dialects if possible (e.g., 'Penang' vs 'Singapore' Laksa). "
            "6. CULTURAL CONTEXT: Always include Cultural Context when relevant to disambiguate local variants. "
            "2. NUTRITION: Estimate nutrition based on visual cues (e.g., portion size, oil sheen). "
            "3. SAFETY: Flag potential health risks (e.g., 'High Sodium', 'High Sugar', 'Hidden Lard'). "
            "4. CONFIDENCE: Return a score (0.0-1.0). If uncertain (<0.75), the system will fallback. "
            "5. OUTPUT: Strictly return a JSON object matching the MealState schema."
        )
        
        self.system_prompt = system_prompt
        self.agent = _LazyMealStateAgent(self.model, self.system_prompt)
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
            nutrition=Nutrition(
                calories=0,
                carbs_g=0,
                sugar_g=0,
                protein_g=0,
                fat_g=0,
                sodium_mg=0,
            ),
            visual_anomalies=["Image uncertainty"],
            suggested_modifications=[
                "Clarification needed: please retake the photo with better lighting.",
                "Clarification needed: capture the whole dish from top-down angle.",
            ],
        )
        return VisionResult(
            primary_state=state,
            raw_ai_output=message,
            needs_manual_review=True,
            processing_latency_ms=latency_ms,
            model_version=getattr(self.model, "model_name", "unknown"),
        )

    def _get_fallback_nutrition(self, dish_name: str) -> Nutrition:
        """Retrieves standard nutritional data from the mock HPB database."""
        data = HPB_DATABASE.get(dish_name)
        if not data:
            # Generic fallback if dish not found
            return Nutrition(
                calories=500, carbs_g=60, sugar_g=10, protein_g=20, fat_g=20, sodium_mg=1000
            )
        return Nutrition(
            calories=data["calories"],
            carbs_g=data["carbs_g"],
            sugar_g=data["sugar_g"],
            protein_g=data["protein_g"],
            fat_g=data["fat_g"],
            sodium_mg=data["sodium_mg"],
            fiber_g=data["fiber_g"]
        )

    def _apply_fallback_logic(self, state: MealState) -> MealState:
        """
        Applies Tier 3 Safe-Fail Fallback.
        Overwrites AI estimates with standard HPB data for safety if confidence is low.
        """
        logger.warning(f"Low confidence ({state.confidence_score}) detected for {state.dish_name}. Applying HPB Fallback.")
        fallback_state = state.model_copy(deep=True)
        
        # 1. Flag method
        fallback_state.identification_method = "HPB_Fallback"
        
        # 2. Match dish to DB (fuzzy match could be added here, for now exact match)
        # In a real system, we might use string similarity or a vector search.
        # Here we try to find the best key match.
        matched_key = None
        normalized_dish_name = self._normalize_dish_lookup_name(fallback_state.dish_name)
        for key in HPB_DATABASE:
            normalized_key = self._normalize_dish_lookup_name(key)
            if normalized_key and normalized_key in normalized_dish_name:
                matched_key = key
                break
        
        if matched_key:
            db_data = HPB_DATABASE[matched_key]
            # Overwrite nutrition
            fallback_state.nutrition = self._get_fallback_nutrition(matched_key)
            # Update Glycemic Index
            fallback_state.glycemic_index_estimate = db_data.get("glycemic_index", GlycemicIndexLevel.UNKNOWN)
            # Update Ingredients (merge or replace)
            # For fallback, we replace to ensure accuracy of the 'standard' version
            fallback_state.ingredients = [
                Ingredient(name=ing) for ing in db_data.get("ingredients", [])
            ]
            # Update Localization
            fallback_state.localization.variant = db_data.get("local_variant")
            fallback_state.suggested_modifications.append("Nutrition data replaced with standard Health Promotion Board values due to low image clarity.")
        else:
            fallback_state.suggested_modifications.append("Dish not found in standard database. Manual review recommended.")
            
        return fallback_state

    def _normalize_dish_lookup_name(self, name: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()

    def _build_prompt(self, image_input: Any) -> tuple[str, str | None, str | None]:
        prompt = "Analyze the provided input and generate a MealState."
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

    async def analyze_dish(
        self,
        image_input: Any,
        user_id: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
    ) -> VisionResult:
        """
        Analyzes a dish image (simulated or real).
        
        Args:
            image_input: In a real scenario, bytes or PIL Image. 
                         For this implementation, we assume the agent handles it 
                         or we pass a description if image processing isn't fully wired.
        """
        started = time.perf_counter()
        request_id = request_id or str(uuid4())
        try:
            # In a real implementation with pydantic-ai and multimodal models:
            # result = await self.agent.run("Analyze this image.", files=[image_input])
            # For this exercise, we assume the input might be a description or we simulate the run.
            # If image_input is a string (description), we pass it.
            
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

            if (
                isinstance(image_input, ImageInput)
                and not self.inference_engine.supports(InferenceModality.IMAGE)
            ):
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
            
            if get_settings().use_inference_engine_v2:
                request = InferenceRequest(
                    request_id=request_id,
                    user_id=user_id,
                    modality=InferenceModality.IMAGE if isinstance(image_input, ImageInput) else InferenceModality.TEXT,
                    payload={"prompt": prompt},
                    runtime_profile={
                        "provider": self.provider,
                        "model": str(getattr(self.model, "model_name", "unknown")),
                    },
                    trace_context={"source": source or "unknown", "filename": filename or "unknown"},
                    output_schema=MealState,
                    system_prompt=self.system_prompt,
                )
                inference = await self.inference_engine.infer(request)
                meal_state = cast(MealState, inference.structured_output)
            else:
                result = await self.agent.run(prompt)
                if not isinstance(result.output, MealState):
                    raise TypeError("Model output is not a MealState payload.")
                meal_state = cast(MealState, result.output)
            
            needs_review = False

            # Guardrails Check
            # 1) Extremely low confidence: deterministic clarification flow
            if meal_state.confidence_score < 0.4:
                elapsed = (time.perf_counter() - started) * 1000.0
                logger.info(
                    "hawker_vision_clarification request_id=%s user_id=%s reason=low_confidence confidence=%.3f latency_ms=%.2f",
                    request_id,
                    user_id,
                    meal_state.confidence_score,
                    elapsed,
                )
                if elapsed >= SLOW_INFERENCE_WARNING_MS:
                    logger.warning(
                        "hawker_vision_slow_inference request_id=%s user_id=%s provider=%s model=%s latency_ms=%.2f latency_human=%s threshold_ms=%.0f",
                        request_id,
                        user_id,
                        self.provider,
                        getattr(self.model, "model_name", "unknown"),
                        elapsed,
                        self._format_latency_ms(elapsed),
                        SLOW_INFERENCE_WARNING_MS,
                    )
                clarification = self._build_clarification_response(
                    reason="Clarification required due to low confidence",
                    confidence_score=meal_state.confidence_score,
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

            # 2) Low but not critical: apply safe HPB fallback and mark for review
            if meal_state.confidence_score < 0.75:
                meal_state = self._apply_fallback_logic(meal_state)
                meal_state.suggested_modifications.append(
                    "Ask for Clarification: request a clearer image or alternate angle."
                )
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
                raw_ai_output=(
                    
                        f"Processed via {self.provider}:{getattr(self.model, 'model_name', 'unknown')}"
                        if meal_state.identification_method == "AI_Flash"
                        else "Fallback Applied"
                    
                ),
                needs_manual_review=needs_review,
                processing_latency_ms=elapsed,
                model_version=getattr(self.model, "model_name", "unknown")
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
        multi_item_count = 1
        if isinstance(image_input, ImageInput):
            raw = image_input.metadata.get("multi_item_count", "1")
            try:
                multi_item_count = max(1, int(raw))
            except ValueError:
                multi_item_count = 1
        record = MealRecognitionRecord(
            id=str(uuid4()),
            user_id=user_id,
            captured_at=datetime.now(timezone.utc),
            source=getattr(image_input, "source", "unknown"),
            meal_state=result.primary_state,
            analysis_version="hawker_vision_v2",
            multi_item_count=multi_item_count,
        )
        logger.info(
            "hawker_vision_analyze_and_record_complete user_id=%s record_id=%s multi_item_count=%s",
            user_id,
            record.id,
            record.multi_item_count,
        )
        return result, record
