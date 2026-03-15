"""API-level meal orchestration use cases.

These functions bridge FastAPI request/response types with the domain layer.
Phase 3 cleanup: decouple FastAPI Request/UploadFile from the application layer.
"""

from __future__ import annotations

import asyncio
import time
from datetime import date
from typing import Any, cast

from fastapi import Request, UploadFile

from care_pilot.features.meals.deps import MealDeps
from apps.api.carepilot_api.errors import build_api_error
from apps.api.carepilot_api.schemas import (
    CursorPageResponse,
    MealAnalyzeResponse,
    DailyNutritionTotalsResponse,
    MealDailySummaryResponse,
    MealRecordsResponse,
    MealWeeklySummaryDayResponse,
    MealWeeklySummaryResponse,
    WorkflowResponse,
)
from care_pilot.features.meals.domain.models import ImageInput
from care_pilot.features.profiles.domain.health_profile import get_or_create_health_profile
from care_pilot.features.meals.logging import (
    build_meal_analysis_log_payload,
    log_meal_analysis_event,
    resolve_meal_analysis_model_name,
)
from care_pilot.platform.auth.session_context import build_user_profile_from_session
from care_pilot.platform.storage.media.ingestion import (
    build_capture_envelope,
    should_suppress_duplicate_capture,
)
from care_pilot.platform.storage.media.upload import SUPPORTED_IMAGE_TYPES, _maybe_downscale_image
from care_pilot.features.meals.domain.models import (
    ContextSnapshot,
    NutritionRiskProfile,
)
from care_pilot.features.meals.workflows.meal_upload_graph import MealUploadDeps, run_meal_upload_workflow
from care_pilot.features.meals.workflows.meal_upload_state import MealUploadState
from care_pilot.shared.time import local_date_for


def _context_snapshot(*, session: dict[str, object]) -> ContextSnapshot:
    return ContextSnapshot(
        user_context_snapshot={
            "profile_mode": str(session.get("profile_mode", "")),
            "display_name": str(session.get("display_name", "")),
        }
    )


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
    analysis_started = time.perf_counter()
    try:
        workflow_output = await asyncio.wait_for(
            run_meal_upload_workflow(
                deps=MealUploadDeps(stores=deps.stores, event_timeline=deps.event_timeline),
                state=MealUploadState(
                    request_id=capture.request_id,
                    correlation_id=capture.correlation_id,
                    user_id=user_profile.id,
                    profile_mode=user_profile.profile_mode,
                    capture=capture,
                    image_input=image_input,
                    provider=routed_provider,
                    meal_text=meal_text,
                    context=_context_snapshot(session=session),
                ),
            ),
            timeout=deps.settings.llm.inference.wall_clock_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise build_api_error(
            status_code=504,
            code="llm.timeout",
            message="meal analysis timed out",
            details={"timeout_seconds": deps.settings.llm.inference.wall_clock_timeout_seconds},
        ) from exc

    latency_ms = (time.perf_counter() - analysis_started) * 1000
    vision_result = workflow_output.raw_observation.vision_result
    log_provider = vision_result.provider or routed_provider or str(deps.settings.llm.provider)
    log_model = vision_result.model_version or resolve_meal_analysis_model_name(deps.settings.llm, log_provider)
    log_payload = build_meal_analysis_log_payload(
        user_id=user_profile.id,
        request_id=capture.request_id,
        correlation_id=capture.correlation_id,
        provider=log_provider,
        model_name=log_model,
        observation_id=workflow_output.raw_observation.observation_id,
        meal_id=workflow_output.validated_event.event_id,
        meal_name=workflow_output.validated_event.meal_name,
        manual_review=bool(workflow_output.validated_event.needs_manual_review),
        latency_ms=latency_ms,
        inference_latency_ms=vision_result.processing_latency_ms,
        unresolved_count=len(workflow_output.raw_observation.unresolved_conflicts),
        risk_tags=workflow_output.nutrition_profile.risk_tags,
    )
    log_meal_analysis_event(log_payload)
    return MealAnalyzeResponse(
        raw_observation=workflow_output.raw_observation,
        validated_event=workflow_output.validated_event,
        nutrition_profile=workflow_output.nutrition_profile,
        output_envelope=workflow_output.output_envelope,
        workflow=WorkflowResponse.model_validate(workflow_output.workflow.model_dump(mode="json")),
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
    records.sort(key=lambda record: record.captured_at, reverse=True)
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
