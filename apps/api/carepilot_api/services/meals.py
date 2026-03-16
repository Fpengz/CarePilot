"""API meal service — thin shim.

This module handles FastAPI request/response concerns and delegates
feature logic to care_pilot.features.meals.use_cases.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast

from fastapi import Request, UploadFile

from apps.api.carepilot_api.errors import build_api_error
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
from care_pilot.features.meals.domain.models import ContextSnapshot, ImageInput
from care_pilot.features.meals.use_cases import (
    MealCandidateInvalidStateError,
    MealCandidateNotFoundError,
    analyze_meal_upload,
    confirm_meal_candidate,
    get_daily_summary_data,
    get_weekly_summary_data,
    list_meal_records_page,
    log_meal_analysis_completion,
)
from care_pilot.features.meals.workflows.meal_upload_state import MealUploadState
from care_pilot.platform.auth.session_context import build_user_profile_from_session
from care_pilot.platform.storage.media.ingestion import (
    build_capture_envelope,
    should_suppress_duplicate_capture,
)
from care_pilot.platform.storage.media.upload import SUPPORTED_IMAGE_TYPES, _maybe_downscale_image


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
    user_profile = build_user_profile_from_session(session, deps.stores.profiles)
    dedupe_state = cast(
        dict[str, Any], request.app.state.__dict__.setdefault("_capture_dedupe_state", {})
    )
    if should_suppress_duplicate_capture(
        dedupe_state,
        capture,
        window_seconds=5,
        session_key=user_profile.id,
    ):
        raise build_api_error(
            status_code=409,
            code="meal.duplicate_capture",
            message="duplicate capture suppressed",
        )
    selected_provider = provider.strip() if isinstance(provider, str) else ""
    routed_provider = (
        selected_provider
        if selected_provider
        else (None if deps.settings.llm.capability_map else deps.settings.llm.provider)
    )

    try:
        latency_ms, workflow_output = await analyze_meal_upload(
            deps=deps,
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
        validated_event=workflow_output.validated_event,
        nutrition_profile=workflow_output.nutrition_profile,
        output_envelope=workflow_output.output_envelope,
        workflow=WorkflowResponse.model_validate(workflow_output.workflow.model_dump(mode="json")),
    )


def confirm_meal(
    *,
    deps: MealDeps,
    user_id: str,
    candidate_id: str,
    action: str,
) -> dict[str, object]:
    try:
        record = confirm_meal_candidate(
            deps=deps, user_id=user_id, candidate_id=candidate_id, action=action
        )
    except MealCandidateNotFoundError as exc:
        raise build_api_error(status_code=404, code="meal.candidate.not_found", message=str(exc))
    except MealCandidateInvalidStateError as exc:
        raise build_api_error(status_code=400, code="meal.candidate.invalid", message=str(exc))

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
    if cursor is None:
        start = 0
    else:
        raw = cursor.strip()
        if not raw.isdigit():
            raise build_api_error(
                status_code=400,
                code="meal.invalid_cursor",
                message="invalid cursor",
                details={"cursor": cursor},
            )
        start = int(raw)
    page = list_meal_records_page(deps=deps, user_id=user_id, limit=limit, cursor=start)
    next_cursor = str(page.next_cursor) if page.next_cursor is not None else None
    return MealRecordsResponse(
        records=page.records,
        page=CursorPageResponse(
            limit=limit,
            cursor=cursor,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
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
        date=summary.date,
        meal_count=summary.meal_count,
        last_logged_at=datetime.fromisoformat(summary.last_logged_at)
        if summary.last_logged_at
        else None,
        consumed=DailyNutritionTotalsResponse.model_validate(summary.consumed.model_dump()),
        targets=DailyNutritionTotalsResponse.model_validate(summary.targets.model_dump()),
        remaining=DailyNutritionTotalsResponse.model_validate(summary.remaining.model_dump()),
        insights=[],
        recommendation_hints=summary.recommendation_hints,
    )


def get_weekly_summary(
    *,
    deps: MealDeps,
    user_id: str,
    week_start: date,
) -> MealWeeklySummaryResponse:
    summary = get_weekly_summary_data(deps=deps, user_id=user_id, week_start=week_start)
    breakdown = {
        day: MealWeeklySummaryDayResponse(
            meal_count=int(values.get("meal_count", 0)),
            calories=float(values.get("calories", 0.0)),
            sugar_g=float(values.get("sugar_g", 0.0)),
            sodium_mg=float(values.get("sodium_mg", 0.0)),
        )
        for day, values in summary.daily_breakdown.items()
    }
    return MealWeeklySummaryResponse(
        week_start=summary.week_start,
        week_end=summary.week_end,
        meal_count=summary.meal_count,
        totals=DailyNutritionTotalsResponse.model_validate(summary.totals.model_dump()),
        daily_breakdown=breakdown,
        pattern_flags=summary.pattern_flags,
    )


__all__ = [
    "analyze_meal",
    "confirm_meal",
    "get_daily_summary",
    "get_weekly_summary",
    "list_meal_records",
]
