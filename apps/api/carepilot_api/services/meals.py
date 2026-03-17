"""
Provide the meal API service.

This module orchestrates meal analysis and confirmation workflows, bridging
the API layer to the feature domain.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from fastapi import HTTPException, Request

from apps.api.carepilot_api.errors import build_api_error
from care_pilot.core.contracts.agent_envelopes import CaptureEnvelope
from care_pilot.core.contracts.api import (
    CursorPageResponse,
    DailyNutritionTotalsResponse,
    MealAnalyzeResponse,
    MealDailySummaryResponse,
    MealRecordsResponse,
    MealWeeklySummaryDayResponse,
    MealWeeklySummaryResponse,
    WorkflowResponse,
)
from care_pilot.features.meals.deps import MealDeps
from care_pilot.features.meals.domain.models import (
    ImageInput,
    NutritionRiskProfile,
    ValidatedMealEvent,
)
from care_pilot.features.meals.meal_service import (
    MealCandidateInvalidStateError,
    MealCandidateNotFoundError,
    analyze_meal_upload,
    build_context_snapshot,
    confirm_meal_candidate,
    get_daily_summary_data,
    get_weekly_summary_data,
    list_meal_records_page,
    log_meal_analysis_completion,
)
from care_pilot.features.meals.workflows.meal_upload_state import MealUploadState

logger = logging.getLogger(__name__)


async def analyze_meal(
    *,
    request: Request,
    deps: MealDeps,
    session: dict[str, Any],
    file: Any,
    provider: str | None = None,
    meal_text: str | None = None,
) -> MealAnalyzeResponse:
    user_id = str(session["user_id"])
    user_profile = deps.stores.profiles.get_health_profile(user_id)
    if user_profile is None:
        raise HTTPException(status_code=404, detail="user profile not found")

    # Validate file payload
    if not file.content_type:
        raise build_api_error(
            status_code=400,
            code="meal.unsupported_image_format",
            message="unsupported image format",
        )

    raw_bytes = await file.read()
    if not raw_bytes:
        raise build_api_error(
            status_code=400,
            code="meal.empty_upload",
            message="empty upload",
        )

    if len(raw_bytes) > deps.settings.api.meal_upload_max_bytes:
        raise build_api_error(
            status_code=413,
            code="meal.upload_too_large",
            message="upload exceeds maximum allowed size",
        )

    image_input = ImageInput(
        source="upload",
        content=raw_bytes,
        mime_type=file.content_type or "image/jpeg",
        filename=file.filename,
    )

    # Use request context IDs for observability contract propagation
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    captured_at = datetime.now(UTC)
    content_sha = hashlib.sha256(raw_bytes).hexdigest()

    capture = CaptureEnvelope(
        capture_id=str(uuid.uuid4()),
        request_id=request_id,
        correlation_id=correlation_id,
        user_id=user_profile.user_id,
        source="upload",
        modality="image",
        mime_type=file.content_type or "image/jpeg",
        filename=file.filename,
        content_sha256=content_sha,
        captured_at=captured_at,
    )

    # Deduplication
    cache_store = getattr(request.app.state.ctx, "cache_store", None)
    if cache_store:
        cache_key = f"capture_dedupe:{user_profile.user_id}:{content_sha}"
        if cache_store.get_json(cache_key):
            raise build_api_error(
                status_code=409,
                code="meal.duplicate_capture",
                message="duplicate capture suppressed",
            )
        cache_store.set_json(cache_key, True, ttl_seconds=30)

    selected_provider = provider.strip() if isinstance(provider, str) else ""
    routed_provider = (
        selected_provider
        if selected_provider
        else (None if deps.settings.llm.capability_map else deps.settings.llm.provider)
    )

    context_snapshot = build_context_snapshot(
        session=session,
        request_id=request_id,
        correlation_id=correlation_id,
        user_agent=request.headers.get("user-agent"),
        client_ip=request.client.host if request.client else None,
    )
    deps.event_timeline.append(
        event_type="context_ingested",
        workflow_name="meal_analysis",
        correlation_id=correlation_id,
        request_id=request_id,
        user_id=user_profile.user_id,
        payload={
            "profile_mode": str(session.get("profile_mode", "")),
            "display_name": str(session.get("display_name", "")),
            "user_agent": context_snapshot.user_agent,
            "client_ip": context_snapshot.client_ip,
        },
    )

    capture = CaptureEnvelope(
        capture_id=str(uuid.uuid4()),
        request_id=request_id,
        correlation_id=correlation_id,
        user_id=user_profile.user_id,
        source="upload",
        modality="image",
        mime_type=file.content_type or "image/jpeg",
        filename=file.filename,
        content_sha256=content_sha,
        captured_at=captured_at,
    )

    try:
        latency_ms, workflow_output = await analyze_meal_upload(
            deps=deps,
            state=MealUploadState(
                request_id=request_id,
                correlation_id=correlation_id,
                user_id=user_profile.user_id,
                profile_mode=str(session.get("profile_mode", "member")),
                capture=capture,
                image_input=image_input,
                provider=routed_provider,
                meal_text=meal_text,
                context=context_snapshot,
            ),
        )
    except TimeoutError as exc:
        raise build_api_error(
            status_code=504,
            code="llm.timeout",
            message="meal analysis timed out",
            details={"timeout_seconds": deps.settings.llm.inference.wall_clock_timeout_seconds},
        ) from exc

    log_meal_analysis_completion(
        deps=deps,
        workflow_output=workflow_output,
        routed_provider=routed_provider,
        latency_ms=latency_ms,
    )
    return MealAnalyzeResponse(
        raw_observation=workflow_output.raw_observation,
        candidate_event=workflow_output.candidate_record.candidate_event,
        candidate_id=workflow_output.candidate_record.candidate_id,
        confirmation_required=workflow_output.confirmation_required,
        validated_event=workflow_output.validated_event
        or ValidatedMealEvent(
            event_id=workflow_output.candidate_record.candidate_id,
            user_id=user_profile.user_id,
            captured_at=captured_at,
            meal_name=workflow_output.candidate_record.candidate_event.meal_name,
        ),
        nutrition_profile=workflow_output.nutrition_profile
        or NutritionRiskProfile(
            event_id=workflow_output.candidate_record.candidate_id,
            user_id=user_profile.user_id,
            captured_at=captured_at,
            calories=0,
            carbs_g=0,
            protein_g=0,
            fat_g=0,
            sugar_g=0,
            sodium_mg=0,
            fiber_g=0,
        ),
        output_envelope=workflow_output.output_envelope,
        workflow=WorkflowResponse.model_validate(workflow_output.workflow.model_dump(mode="json")),
    )


async def confirm_meal(
    *,
    deps: MealDeps,
    user_id: str,
    candidate_id: str,
    action: str,
    session_id: str | None,
    user_name: str | None,
) -> dict[str, object]:
    try:
        record = await confirm_meal_candidate(
            deps=deps,
            user_id=user_id,
            candidate_id=candidate_id,
            action=action,
            session_id=session_id,
            user_name=user_name,
        )
    except MealCandidateNotFoundError as exc:
        raise build_api_error(
            status_code=404, code="meal.candidate.not_found", message=str(exc)
        ) from exc
    except MealCandidateInvalidStateError as exc:
        raise build_api_error(
            status_code=400, code="meal.candidate.invalid", message=str(exc)
        ) from exc

    return {
        "status": record.confirmation_status,
        "candidate_id": record.candidate_id,
        "meal_name": record.candidate_event.meal_name,
    }


def list_meal_records(
    *,
    deps: MealDeps,
    user_id: str,
    limit: int = 50,
    cursor: str | None = None,
) -> MealRecordsResponse:
    # Handle string cursor from API
    int_cursor = 0
    if cursor:
        if not cursor.isdigit():
            raise build_api_error(
                status_code=400,
                code="meal.invalid_cursor",
                message="invalid cursor",
            )
        int_cursor = int(cursor)

    page = list_meal_records_page(deps=deps, user_id=user_id, limit=limit, cursor=int_cursor)
    return MealRecordsResponse(
        records=page.records,
        page=CursorPageResponse(
            limit=limit,
            cursor=cursor,
            next_cursor=str(page.next_cursor) if page.next_cursor is not None else None,
            has_more=bool(page.next_cursor is not None),
            returned=page.returned,
        ),
    )


def get_daily_summary(
    *,
    deps: MealDeps,
    user_id: str,
    summary_date: date,
) -> MealDailySummaryResponse:
    summary = get_daily_summary_data(deps=deps, user_id=user_id, summary_date=summary_date)
    return MealDailySummaryResponse(
        date=str(summary_date),
        meal_count=summary.meal_count,
        consumed=DailyNutritionTotalsResponse.model_validate(summary.consumed.model_dump()),
        targets=DailyNutritionTotalsResponse.model_validate(summary.targets.model_dump()),
        remaining=DailyNutritionTotalsResponse.model_validate(summary.remaining.model_dump()),
    )


def get_weekly_summary(
    *,
    deps: MealDeps,
    user_id: str,
    week_start: date,
) -> MealWeeklySummaryResponse:
    summary = get_weekly_summary_data(deps=deps, user_id=user_id, week_start=week_start)
    return MealWeeklySummaryResponse(
        week_start=summary.week_start,
        week_end=summary.week_end,
        meal_count=summary.meal_count,
        totals=DailyNutritionTotalsResponse.model_validate(summary.totals.model_dump()),
        daily_breakdown={
            d: MealWeeklySummaryDayResponse(
                meal_count=int(item["meal_count"]),
                calories=float(item["calories"]),
                sugar_g=float(item["sugar_g"]),
                sodium_mg=float(item["sodium_mg"]),
            )
            for d, item in summary.daily_breakdown.items()
        },
        pattern_flags=summary.pattern_flags,
    )
