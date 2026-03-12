"""API-level meal orchestration use cases.

These functions bridge FastAPI request/response types with the domain layer.
Phase 3 cleanup: decouple FastAPI Request/UploadFile from the application layer.
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import date
from typing import TYPE_CHECKING, Any, cast

from fastapi import Request, UploadFile
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from dietary_guardian.features.meals.deps import MealDeps
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    CursorPageResponse,
    MealAnalyzeResponse,
    DailyNutritionTotalsResponse,
    MealDailySummaryResponse,
    MealRecordsResponse,
    MealWeeklySummaryDayResponse,
    MealWeeklySummaryResponse,
    WorkflowResponse,
)
from dietary_guardian.agent.core import AgentContext
from dietary_guardian.agent.runtime import LLMFactory
from dietary_guardian.features.meals.domain import MealPerception, MealPortionEstimate, PerceivedMealItem
from dietary_guardian.features.meals.domain.agent_schemas import MealAnalysisAgentInput
from dietary_guardian.features.meals.domain.models import ImageInput
from dietary_guardian.features.profiles.domain.health_profile import get_or_create_health_profile
from dietary_guardian.features.meals.use_cases import normalize_vision_result
from dietary_guardian.platform.auth.session_context import build_user_profile_from_session
from dietary_guardian.platform.storage.media.ingestion import (
    build_capture_envelope,
    should_suppress_duplicate_capture,
)
from dietary_guardian.platform.storage.media.upload import SUPPORTED_IMAGE_TYPES, _maybe_downscale_image
from dietary_guardian.features.meals.domain.models import (
    ContextSnapshot,
    DietaryClaim,
    DietaryClaims,
    NutritionRiskProfile,
    RawObservationBundle,
    ValidatedMealEvent,
)
from dietary_guardian.shared.time import local_date_for

if TYPE_CHECKING:
    from dietary_guardian.agent.meal_analysis.vision_module import HawkerVisionModule as HawkerVisionModuleType

class _ArbitrationDecision(BaseModel):
    chosen_label: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str | None = None


def _build_hawker_vision_module(*, provider: str | None, food_store: Any) -> "HawkerVisionModuleType":
    from dietary_guardian.agent.meal_analysis import vision_module  # noqa: PLC0415

    HawkerVisionModule = cast("type[HawkerVisionModuleType]", vision_module.HawkerVisionModule)
    params = inspect.signature(HawkerVisionModule).parameters
    if "food_store" in params:
        return HawkerVisionModule(provider=provider, food_store=food_store)
    return HawkerVisionModule(provider=provider)


def _extract_dietary_claims(*, text: str | None) -> DietaryClaims:
    if not text:
        return DietaryClaims()
    lowered = text.lower()
    claims: list[DietaryClaim] = []
    for token in ("rice", "chicken", "fish", "noodles", "milo", "tea", "coffee"):
        if token in lowered:
            claims.append(DietaryClaim(label=token, confidence=0.65))
    consumption_fraction = 1.0
    if "half" in lowered or "1/2" in lowered:
        consumption_fraction = 0.5
    if "quarter" in lowered or "1/4" in lowered:
        consumption_fraction = 0.25
    return DietaryClaims(
        claimed_items=claims,
        consumption_fraction=consumption_fraction,
        meal_time_label="breakfast" if "breakfast" in lowered else "lunch" if "lunch" in lowered else None,
        vendor_or_source=None,
        preparation_override="no sugar" if "no sugar" in lowered else None,
        dietary_constraints=[item for item in ("no sugar", "less salt") if item in lowered],
        goal_context=None,
        certainty_level="high" if claims else "low",
        ambiguity_notes=[],
    )


def _context_snapshot(*, session: dict[str, object]) -> ContextSnapshot:
    return ContextSnapshot(
        user_context_snapshot={
            "profile_mode": str(session.get("profile_mode", "")),
            "display_name": str(session.get("display_name", "")),
        }
    )


def _claim_perception(labels: list[str], confidence: float) -> MealPerception:
    items = [
        PerceivedMealItem(
            label=label,
            candidate_aliases=[label],
            portion_estimate=MealPortionEstimate(amount=1.0, unit="serving", confidence=confidence),
            confidence=confidence,
        )
        for label in labels
        if label
    ]
    return MealPerception(items=items, confidence_score=confidence, image_quality="unknown")


async def _arbitrate_label(
    *,
    vision_labels: list[str],
    claim_labels: list[str],
    user_text: str | None,
    provider: str | None,
) -> _ArbitrationDecision | None:
    if not user_text or not vision_labels or not claim_labels:
        return None
    model = LLMFactory.get_model(provider=provider)
    agent = Agent(
        model,
        output_type=_ArbitrationDecision,
        system_prompt=(
            "You are a reconciliation arbiter. Choose the most plausible food label based on evidence. "
            "Return strict JSON with chosen_label, confidence, rationale."
        ),
    )
    prompt = (
        f"Vision labels: {vision_labels}\n"
        f"User claims: {claim_labels}\n"
        f"User text: {user_text}\n"
        "Select the best single label. If uncertain, choose the most specific plausible label."
    )
    try:
        result = await agent.run(prompt)
    except Exception:
        return None
    return result.output if isinstance(result.output, _ArbitrationDecision) else None


async def analyze_meal(
    *,
    request: Request,
    deps: MealDeps,
    session: dict[str, object],
    file: UploadFile,
    provider: str | None,
    meal_text: str | None = None,
) -> MealAnalyzeResponse:
    payload = await file.read()
    if len(payload) > deps.settings.api.meal_upload_max_bytes:
        raise build_api_error(
            status_code=413,
            code="meal.upload_too_large",
            message="upload exceeds maximum allowed size",
            details={"max_bytes": int(deps.settings.api.meal_upload_max_bytes)},
        )
    if len(payload) == 0:
        raise build_api_error(status_code=400, code="meal.empty_upload", message="empty upload")
    mime_type = file.content_type or ""
    if mime_type not in SUPPORTED_IMAGE_TYPES:
        raise build_api_error(
            status_code=400,
            code="meal.unsupported_image_format",
            message="unsupported image format",
        )

    image_bytes, preprocess_meta = _maybe_downscale_image(
        payload,
        mime_type,
        enabled=deps.settings.app.image_downscale_enabled,
        max_side_px=deps.settings.app.image_max_side_px,
    )
    image_input = ImageInput(
        source="upload",
        filename=file.filename,
        mime_type=mime_type,
        content=image_bytes,
        metadata=preprocess_meta,
    )
    capture = build_capture_envelope(
        image_input,
        user_id=str(session["user_id"]),
        request_id=getattr(request.state, "request_id", None),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    dedupe_state = cast(dict[str, Any], request.app.state.__dict__.setdefault("_capture_dedupe_state", {}))
    if should_suppress_duplicate_capture(dedupe_state, capture, window_seconds=30):
        raise build_api_error(
            status_code=409,
            code="meal.duplicate_capture",
            message="duplicate capture suppressed",
        )

    user_profile = build_user_profile_from_session(session, deps.stores.profiles)
    selected_provider = provider.strip() if isinstance(provider, str) else ""
    routed_provider = (
        selected_provider
        if selected_provider
        else (None if deps.settings.llm.capability_map else deps.settings.llm.provider)
    )
    agent = cast(
        Any,
        _build_hawker_vision_module(
            provider=routed_provider,
            food_store=deps.stores.foods,
        ),
    )
    try:
        if hasattr(agent, "run"):
            result = await asyncio.wait_for(
                agent.run(
                    MealAnalysisAgentInput(
                        image_input=image_input,
                        user_id=user_profile.id,
                        request_id=capture.request_id,
                        correlation_id=capture.correlation_id,
                        persist_record=True,
                    ),
                    AgentContext(
                        user_id=user_profile.id,
                        request_id=capture.request_id,
                        correlation_id=capture.correlation_id,
                    ),
                ),
                timeout=deps.settings.llm.inference.wall_clock_timeout_seconds,
            )
        else:
            vision_result, meal_record = await asyncio.wait_for(
                agent.analyze_and_record(
                    image_input,
                    user_profile.id,
                    request_id=capture.request_id,
                    correlation_id=capture.correlation_id,
                ),
                timeout=deps.settings.llm.inference.wall_clock_timeout_seconds,
            )
            result = type(
                "_LegacyMealAnalysisResult",
                (),
                {
                    "output": type(
                        "_LegacyMealAnalysisOutput",
                        (),
                        {
                            "vision_result": vision_result,
                            "meal_record": meal_record,
                        },
                    )(),
                },
            )()
    except asyncio.TimeoutError as exc:
        raise build_api_error(
            status_code=504,
            code="llm.timeout",
            message="meal analysis timed out",
            details={"timeout_seconds": deps.settings.llm.inference.wall_clock_timeout_seconds},
        ) from exc
    if result.output is None or result.output.meal_record is None:
        raise build_api_error(
            status_code=500,
            code="meal.agent_failed",
            message="meal analysis agent returned no meal record",
        )
    vision_result = result.output.vision_result
    claims = _extract_dietary_claims(text=meal_text)
    unresolved: list[str] = []
    perception = vision_result.perception or MealPerception()
    claim_labels = [item.label for item in claims.claimed_items]
    vision_labels = [item.label for item in perception.items]
    if claim_labels and vision_labels and set(claim_labels) != set(vision_labels):
        unresolved.append("claim_vs_vision_conflict")
        decision = await _arbitrate_label(
            vision_labels=vision_labels,
            claim_labels=claim_labels,
            user_text=meal_text,
            provider=deps.settings.llm.provider,
        )
        if decision and decision.chosen_label:
            claim_labels = [decision.chosen_label]
            unresolved = []
    reconciled_perception = _claim_perception(claim_labels, confidence=0.6) if claim_labels else perception
    reconciled = normalize_vision_result(
        vision_result=vision_result.model_copy(update={"perception": reconciled_perception}),
        food_store=deps.stores.foods,
    )
    raw_observation = RawObservationBundle(
        user_id=user_profile.id,
        source=image_input.source,
        vision_result=vision_result,
        dietary_claims=claims,
        context=_context_snapshot(session=session),
        image_quality=getattr(reconciled.perception, "image_quality", None) if reconciled.perception else None,
        confidence_score=getattr(reconciled.perception, "confidence_score", 0.0) if reconciled.perception else 0.0,
        unresolved_conflicts=unresolved,
    )
    enriched_event = reconciled.enriched_event
    if enriched_event is None:
        raise build_api_error(
            status_code=500,
            code="meal.analysis_failed",
            message="meal analysis produced no canonical event",
        )
    validated_event = ValidatedMealEvent(
        user_id=user_profile.id,
        captured_at=raw_observation.captured_at,
        meal_name=enriched_event.meal_name,
        consumption_fraction=claims.consumption_fraction,
        canonical_items=list(enriched_event.normalized_items),
        alternatives=list(enriched_event.unresolved_items),
        confidence_summary={
            "vision_confidence": getattr(reconciled.perception, "confidence_score", 0.0) if reconciled.perception else 0.0,
            "claim_count": len(claims.claimed_items),
            "unresolved": list(unresolved),
        },
        provenance={
            "observation_id": raw_observation.observation_id,
            "source": raw_observation.source,
        },
        needs_manual_review=bool(enriched_event.needs_manual_review or unresolved),
    )
    total = enriched_event.total_nutrition
    uncertainty = {}
    if enriched_event.unresolved_items:
        uncertainty = {"calories_range": [max(total.calories * 0.8, 0.0), total.calories * 1.2]}
    nutrition_profile = NutritionRiskProfile(
        event_id=validated_event.event_id,
        user_id=user_profile.id,
        captured_at=validated_event.captured_at,
        calories=total.calories,
        carbs_g=total.carbs_g,
        sugar_g=total.sugar_g,
        protein_g=total.protein_g,
        fat_g=total.fat_g,
        sodium_mg=total.sodium_mg,
        fiber_g=total.fiber_g,
        risk_tags=list(enriched_event.risk_tags),
        uncertainty=uncertainty,
    )
    deps.stores.meals.save_meal_observation(raw_observation)
    deps.stores.meals.save_validated_meal_event(validated_event)
    deps.stores.meals.save_nutrition_risk_profile(nutrition_profile)
    workflow = deps.coordinator.run_meal_analysis_workflow(
        capture=capture,
        vision_result=vision_result,
        user_profile=user_profile,
        meal_record_id=validated_event.event_id,
    )
    return MealAnalyzeResponse(
        raw_observation=raw_observation,
        validated_event=validated_event,
        nutrition_profile=nutrition_profile,
        output_envelope=workflow.output_envelope,
        workflow=WorkflowResponse.model_validate(workflow.model_dump(mode="json")),
    )


def _parse_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    raw = cursor.strip()
    if not raw.isdigit():
        raise build_api_error(
            status_code=400,
            code="meal.invalid_cursor",
            message="invalid cursor",
            details={"cursor": cursor},
        )
    return int(raw)


def list_meal_records(
    *,
    deps: MealDeps,
    user_id: str,
    limit: int = 50,
    cursor: str | None = None,
) -> MealRecordsResponse:
    records = deps.stores.meals.list_validated_meal_events(user_id)
    start = _parse_cursor(cursor)
    end = start + limit
    page_items = records[start:end]
    next_cursor = str(end) if end < len(records) else None
    return MealRecordsResponse(
        records=page_items,
        page=CursorPageResponse(
            limit=limit,
            cursor=cursor,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
            returned=len(page_items),
        ),
    )


def get_daily_summary(
    *,
    deps: MealDeps,
    user_id: str,
    summary_date: date,
) -> MealDailySummaryResponse:
    profile = get_or_create_health_profile(deps.stores.profiles, user_id)
    profiles = deps.stores.meals.list_nutrition_risk_profiles(user_id)
    daily = [
        item
        for item in profiles
        if local_date_for(item.captured_at, timezone_name=deps.settings.app.timezone) == summary_date
    ]
    calories = sum(item.calories for item in daily)
    sugar = sum(item.sugar_g for item in daily)
    sodium = sum(item.sodium_mg for item in daily)
    protein = sum(item.protein_g for item in daily)
    fiber = sum(item.fiber_g for item in daily)
    return MealDailySummaryResponse(
        date=str(summary_date),
        meal_count=len(daily),
        last_logged_at=max((item.captured_at for item in daily), default=None),
        consumed=DailyNutritionTotalsResponse(
            calories=calories,
            sugar_g=sugar,
            sodium_mg=sodium,
            protein_g=protein,
            fiber_g=fiber,
        ),
        targets=DailyNutritionTotalsResponse(
            calories=float(profile.target_calories_per_day or 0.0),
            sugar_g=float(profile.daily_sugar_limit_g),
            sodium_mg=float(profile.daily_sodium_limit_mg),
            protein_g=float(profile.daily_protein_target_g),
            fiber_g=float(profile.daily_fiber_target_g),
        ),
        remaining=DailyNutritionTotalsResponse(
            calories=max(float(profile.target_calories_per_day or 0.0) - calories, 0.0),
            sugar_g=max(float(profile.daily_sugar_limit_g) - sugar, 0.0),
            sodium_mg=max(float(profile.daily_sodium_limit_mg) - sodium, 0.0),
            protein_g=max(float(profile.daily_protein_target_g) - protein, 0.0),
            fiber_g=max(float(profile.daily_fiber_target_g) - fiber, 0.0),
        ),
        insights=[],
        recommendation_hints=[],
    )


def get_weekly_summary(
    *,
    deps: MealDeps,
    user_id: str,
    week_start: date,
) -> MealWeeklySummaryResponse:
    profiles = deps.stores.meals.list_nutrition_risk_profiles(user_id)
    week_end = week_start.fromordinal(week_start.toordinal() + 6)
    week_profiles: list[NutritionRiskProfile] = []
    bucket: dict[str, list[NutritionRiskProfile]] = {}
    for item in profiles:
        day = local_date_for(item.captured_at, timezone_name=deps.settings.app.timezone)
        if day < week_start or day > week_end:
            continue
        week_profiles.append(item)
        bucket.setdefault(str(day), []).append(item)
    totals = DailyNutritionTotalsResponse(
        calories=sum(item.calories for item in week_profiles),
        sugar_g=sum(item.sugar_g for item in week_profiles),
        sodium_mg=sum(item.sodium_mg for item in week_profiles),
        protein_g=sum(item.protein_g for item in week_profiles),
        fiber_g=sum(item.fiber_g for item in week_profiles),
    )
    breakdown = {
        day: MealWeeklySummaryDayResponse(
            meal_count=len(items),
            calories=sum(item.calories for item in items),
            sugar_g=sum(item.sugar_g for item in items),
            sodium_mg=sum(item.sodium_mg for item in items),
        )
        for day, items in bucket.items()
    }
    return MealWeeklySummaryResponse(
        week_start=str(week_start),
        week_end=str(week_end),
        meal_count=sum(len(items) for items in bucket.values()),
        totals=totals,
        daily_breakdown=breakdown,
        pattern_flags=[],
    )


__all__ = ["analyze_meal", "get_daily_summary", "get_weekly_summary", "list_meal_records"]
