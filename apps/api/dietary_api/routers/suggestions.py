from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from dietary_guardian.application.suggestions import (
    MissingActiveHouseholdError,
    NoMealRecordsError,
    SuggestionForbiddenError,
    SuggestionNotFoundError,
    generate_suggestion_from_report,
    get_suggestion_for_session,
    list_suggestions_for_session,
)
from dietary_guardian.application.suggestions.ports import HouseholdStorePort, SuggestionRepositoryPort

from ..auth import build_user_profile_from_session
from ..routes_shared import current_session, get_context, require_scopes
from ..schemas import (
    SuggestionDetailResponse,
    SuggestionGenerateFromReportRequest,
    SuggestionGenerateFromReportResponse,
    SuggestionItemResponse,
    SuggestionListResponse,
)

router = APIRouter(tags=["suggestions"])


def _to_suggestion_response(payload: dict[str, object]) -> SuggestionItemResponse:
    return SuggestionItemResponse.model_validate(payload)


@router.post(
    "/api/v1/suggestions/generate-from-report",
    response_model=SuggestionGenerateFromReportResponse,
)
def suggestions_generate_from_report(
    payload: SuggestionGenerateFromReportRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> SuggestionGenerateFromReportResponse:
    require_scopes(session, {"report:write", "recommendation:generate"})
    context = get_context(request)
    try:
        saved = generate_suggestion_from_report(
            repository=cast(SuggestionRepositoryPort, context.repository),
            clinical_memory=context.clinical_memory,
            session=session,
            text=payload.text,
            request_id=getattr(request.state, "request_id", None),
            correlation_id=getattr(request.state, "correlation_id", None),
            build_user_profile=build_user_profile_from_session,
        )
    except NoMealRecordsError:
        raise HTTPException(status_code=400, detail="no meal records available")
    return SuggestionGenerateFromReportResponse(suggestion=_to_suggestion_response(saved))


@router.get("/api/v1/suggestions", response_model=SuggestionListResponse)
def suggestions_list(
    request: Request,
    scope: str = Query(default="self", pattern="^(self|household)$"),
    limit: int = Query(default=20, ge=1, le=100),
    session: dict[str, object] = Depends(current_session),
) -> SuggestionListResponse:
    require_scopes(session, {"report:read"})
    context = get_context(request)
    try:
        raw_items = list_suggestions_for_session(
            repository=cast(SuggestionRepositoryPort, context.repository),
            household_store=cast(HouseholdStorePort, context.household_store),
            session=session,
            scope=scope,
            limit=limit,
        )
    except MissingActiveHouseholdError:
        raise HTTPException(status_code=400, detail="active household required for household scope")
    except SuggestionForbiddenError:
        raise HTTPException(status_code=403, detail="forbidden")
    items = [_to_suggestion_response(item) for item in raw_items]
    return SuggestionListResponse(items=items)


@router.get("/api/v1/suggestions/{suggestion_id}", response_model=SuggestionDetailResponse)
def suggestions_get(
    suggestion_id: str,
    request: Request,
    scope: str = Query(default="self", pattern="^(self|household)$"),
    session: dict[str, object] = Depends(current_session),
) -> SuggestionDetailResponse:
    require_scopes(session, {"report:read"})
    context = get_context(request)
    try:
        item = get_suggestion_for_session(
            repository=cast(SuggestionRepositoryPort, context.repository),
            household_store=cast(HouseholdStorePort, context.household_store),
            session=session,
            scope=scope,
            suggestion_id=suggestion_id,
        )
    except MissingActiveHouseholdError:
        raise HTTPException(status_code=400, detail="active household required for household scope")
    except SuggestionForbiddenError:
        raise HTTPException(status_code=403, detail="forbidden")
    except SuggestionNotFoundError:
        raise HTTPException(status_code=404, detail="suggestion not found")
    return SuggestionDetailResponse(suggestion=_to_suggestion_response(item))
