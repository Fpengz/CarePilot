"""
Expose meal API endpoints.

This router defines meal capture, analysis, and reporting routes and delegates
to meal API services for orchestration.
"""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

from ..deps import meal_deps
from ..routes_shared import current_session, get_context, require_action
from ..schemas import (
    MealAnalyzeResponse,
    MealConfirmRequest,
    MealConfirmResponse,
    MealDailySummaryResponse,
    MealRecordsResponse,
    MealWeeklySummaryResponse,
)
from ..services.meals import (
    analyze_meal,
    confirm_meal,
    get_daily_summary,
    get_weekly_summary,
    list_meal_records,
)

router = APIRouter(tags=["meals"])


@router.post("/api/v1/meal/analyze", response_model=MealAnalyzeResponse)
async def meal_analyze(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    runtime_mode: Annotated[str, Form()] = "local",
    provider: Annotated[str | None, Form()] = None,
    meal_text: Annotated[str | None, Form()] = None,
    session: Annotated[dict[str, Any], Depends(current_session)] = None,  # type: ignore
) -> MealAnalyzeResponse:
    del runtime_mode
    require_action(session, "meal.analyze")
    return await analyze_meal(
        request=request,
        deps=meal_deps(get_context(request)),
        session=session,
        file=file,
        provider=provider,
        meal_text=meal_text,
    )


@router.get("/api/v1/meal/records", response_model=MealRecordsResponse)
def meal_records(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query()] = None,
    session: Annotated[dict[str, Any], Depends(current_session)] = None,  # type: ignore
) -> MealRecordsResponse:
    require_action(session, "meal.records.read")
    return list_meal_records(
        deps=meal_deps(get_context(request)),
        user_id=str(session["user_id"]),
        limit=limit,
        cursor=cursor,
    )


@router.get("/api/v1/meal/daily-summary", response_model=MealDailySummaryResponse)
def meal_daily_summary(
    request: Request,
    summary_date: Annotated[date, Query(alias="date")],
    session: Annotated[dict[str, Any], Depends(current_session)] = None,  # type: ignore
) -> MealDailySummaryResponse:
    require_action(session, "meal.records.read")
    return get_daily_summary(
        deps=meal_deps(get_context(request)),
        user_id=str(session["user_id"]),
        summary_date=summary_date,
    )


@router.get("/api/v1/meal/weekly-summary", response_model=MealWeeklySummaryResponse)
def meal_weekly_summary(
    request: Request,
    week_start: Annotated[date, Query()],
    session: Annotated[dict[str, Any], Depends(current_session)] = None,  # type: ignore
) -> MealWeeklySummaryResponse:
    require_action(session, "meal.records.read")
    return get_weekly_summary(
        deps=meal_deps(get_context(request)),
        user_id=str(session["user_id"]),
        week_start=week_start,
    )


@router.post("/api/v1/meal/confirm", response_model=MealConfirmResponse)
async def meal_confirm(
    payload: MealConfirmRequest,
    request: Request,
    session: Annotated[dict[str, Any], Depends(current_session)] = None,  # type: ignore
) -> MealConfirmResponse:
    require_action(session, "meal.confirm")
    result = await confirm_meal(
        deps=meal_deps(get_context(request)),
        user_id=str(session["user_id"]),
        candidate_id=payload.candidate_id,
        action=payload.action,
        session_id=str(session.get("session_id")) if session.get("session_id") else None,
        user_name=str(session.get("display_name")) if session.get("display_name") else None,
    )
    return MealConfirmResponse.model_validate(result)
