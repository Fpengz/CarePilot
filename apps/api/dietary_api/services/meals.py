"""API orchestration for meal analysis, history, and nutrition summaries."""

import asyncio
import inspect
from datetime import date
from typing import Any, cast

from fastapi import Request, UploadFile

from apps.api.dietary_api.deps import MealDeps
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    CursorPageResponse,
    MealAnalyzeResponse,
    MealAnalyzeSummaryResponse,
    MealDailySummaryResponse,
    MealRecordsResponse,
    MealWeeklySummaryResponse,
    WorkflowResponse,
)
from dietary_guardian.application.auth.session_context import build_user_profile_from_session
from dietary_guardian.capabilities import MealAnalysisAgent
from dietary_guardian.capabilities.base import AgentContext
from dietary_guardian.capabilities.schemas import MealAnalysisAgentInput
from dietary_guardian.domain.nutrition import (
    build_daily_nutrition_summary,
    build_weekly_nutrition_summary,
)
from dietary_guardian.domain.meals.models import ImageInput, VisionResult
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord
from dietary_guardian.domain.profiles.health_profile import get_or_create_health_profile
from dietary_guardian.infrastructure.media.ingestion import (
    build_capture_envelope,
    should_suppress_duplicate_capture,
)
from dietary_guardian.infrastructure.media.upload import SUPPORTED_IMAGE_TYPES, _maybe_downscale_image

HawkerVisionModule = MealAnalysisAgent


def _build_hawker_vision_module(*, provider: str | None, food_store: Any) -> MealAnalysisAgent:
    params = inspect.signature(HawkerVisionModule).parameters
    if "food_store" in params:
        return HawkerVisionModule(provider=provider, food_store=food_store)
    return HawkerVisionModule(provider=provider)


async def analyze_meal(
    *,
    request: Request,
    deps: MealDeps,
    session: dict[str, object],
    file: UploadFile,
    provider: str | None,
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
        else (None if deps.settings.llm.capability_targets else deps.settings.llm.provider)
    )
    agent = _build_hawker_vision_module(
        provider=routed_provider,
        food_store=deps.stores.foods,
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
                timeout=deps.settings.llm.inference_wall_clock_timeout_seconds,
            )
        else:
            vision_result, meal_record = await asyncio.wait_for(
                agent.analyze_and_record(
                    image_input,
                    user_profile.id,
                    request_id=capture.request_id,
                    correlation_id=capture.correlation_id,
                ),
                timeout=deps.settings.llm.inference_wall_clock_timeout_seconds,
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
            details={"timeout_seconds": deps.settings.llm.inference_wall_clock_timeout_seconds},
        ) from exc
    if result.output is None or result.output.meal_record is None:
        raise build_api_error(
            status_code=500,
            code="meal.agent_failed",
            message="meal analysis agent returned no meal record",
        )
    vision_result = result.output.vision_result
    meal_record = result.output.meal_record
    deps.stores.meals.save_meal_record(meal_record)
    workflow = deps.coordinator.run_meal_analysis_workflow(
        capture=capture,
        vision_result=vision_result,
        user_profile=user_profile,
        meal_record_id=meal_record.id,
    )
    return MealAnalyzeResponse(
        summary=_build_meal_summary(vision_result=vision_result, meal_record=meal_record),
        vision_result=vision_result,
        meal_record=meal_record,
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
    records = deps.stores.meals.list_meal_records(user_id)
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
    records = deps.stores.meals.list_meal_records(user_id)
    summary = build_daily_nutrition_summary(
        profile=profile,
        meal_history=records,
        summary_date=summary_date,
        timezone_name=deps.settings.app.timezone,
    )
    return MealDailySummaryResponse.model_validate(summary.model_dump(mode="json"))


def get_weekly_summary(
    *,
    deps: MealDeps,
    user_id: str,
    week_start: date,
) -> MealWeeklySummaryResponse:
    records = deps.stores.meals.list_meal_records(user_id)
    summary = build_weekly_nutrition_summary(
        meal_history=records,
        week_start=week_start,
        timezone_name=deps.settings.app.timezone,
    )
    return MealWeeklySummaryResponse.model_validate(summary)


def _build_meal_summary(*, vision_result: VisionResult, meal_record: MealRecognitionRecord) -> MealAnalyzeSummaryResponse:
    primary = vision_result.primary_state
    nutrition = primary.nutrition
    flags: list[str] = []
    flags.extend(primary.visual_anomalies)
    if vision_result.needs_manual_review:
        flags.append("manual_review_required")
    # Deduplicate while preserving order.
    deduped_flags = list(dict.fromkeys(str(item) for item in flags if str(item).strip()))
    return MealAnalyzeSummaryResponse(
        meal_record_id=meal_record.id,
        meal_name=primary.dish_name,
        confidence=round(float(primary.confidence_score), 4),
        identification_method=str(primary.identification_method),
        estimated_calories=float(nutrition.calories),
        portion_size=str(primary.portion_size),
        needs_manual_review=bool(vision_result.needs_manual_review),
        flags=deduped_flags,
        portion_notes=list(primary.suggested_modifications),
        captured_at=meal_record.captured_at,
    )
