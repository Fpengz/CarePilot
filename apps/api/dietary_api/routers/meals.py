from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

from ..routes_shared import current_session, get_context, require_action
from ..schemas.meals import MealAnalyzeResponse, MealDailySummaryResponse, MealRecordsResponse, MealWeeklySummaryResponse
from ..services.meals import analyze_meal, get_daily_summary, get_weekly_summary, list_meal_records

router = APIRouter(tags=["meals"])


@router.post("/api/v1/meal/analyze", response_model=MealAnalyzeResponse)
async def meal_analyze(
    request: Request,
    file: UploadFile = File(...),
    runtime_mode: str = Form("local"),
    provider: str | None = Form(default=None),
    session: dict[str, object] = Depends(current_session),
) -> MealAnalyzeResponse:
    del runtime_mode
    require_action(session, "meal.analyze")
    return await analyze_meal(
        request=request,
        context=get_context(request),
        session=session,
        file=file,
        provider=provider,
    )


@router.get("/api/v1/meal/records", response_model=MealRecordsResponse)
def meal_records(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = Query(default=None),
    session: dict[str, object] = Depends(current_session),
) -> MealRecordsResponse:
    require_action(session, "meal.records.read")
    return list_meal_records(
        context=get_context(request),
        user_id=str(session["user_id"]),
        limit=limit,
        cursor=cursor,
    )


@router.get("/api/v1/meal/daily-summary", response_model=MealDailySummaryResponse)
def meal_daily_summary(
    request: Request,
    summary_date: date = Query(alias="date"),
    session: dict[str, object] = Depends(current_session),
) -> MealDailySummaryResponse:
    require_action(session, "meal.records.read")
    return get_daily_summary(
        context=get_context(request),
        user_id=str(session["user_id"]),
        summary_date=summary_date,
    )


@router.get("/api/v1/meal/weekly-summary", response_model=MealWeeklySummaryResponse)
def meal_weekly_summary(
    request: Request,
    week_start: date = Query(),
    session: dict[str, object] = Depends(current_session),
) -> MealWeeklySummaryResponse:
    require_action(session, "meal.records.read")
    return get_weekly_summary(
        context=get_context(request),
        user_id=str(session["user_id"]),
        week_start=week_start,
    )
