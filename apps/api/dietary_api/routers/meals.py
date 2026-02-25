from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from ..routes_shared import current_session, get_context, require_scopes
from ..schemas import MealAnalyzeResponse, MealRecordsResponse
from ..services.meals import analyze_meal, list_meal_records

router = APIRouter(tags=["meals"])


@router.post("/api/v1/meal/analyze", response_model=MealAnalyzeResponse)
async def meal_analyze(
    request: Request,
    file: UploadFile = File(...),
    runtime_mode: str = Form("local"),
    provider: str = Form("test"),
    session: dict[str, object] = Depends(current_session),
) -> MealAnalyzeResponse:
    del runtime_mode
    require_scopes(session, {"meal:write"})
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
    session: dict[str, object] = Depends(current_session),
) -> MealRecordsResponse:
    require_scopes(session, {"meal:read"})
    return list_meal_records(context=get_context(request), user_id=str(session["user_id"]))
