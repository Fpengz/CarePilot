"""API router for suggestions endpoints."""

from fastapi import APIRouter, Depends, Query, Request

from ..routes_shared import current_session, get_context, require_action
from ..schemas import (
    SuggestionDetailResponse,
    SuggestionGenerateFromReportRequest,
    SuggestionGenerateFromReportResponse,
    SuggestionListResponse,
)
from ..services.suggestions import generate_from_report, get_for_session, list_for_session

router = APIRouter(tags=["suggestions"])


@router.post(
    "/api/v1/suggestions/generate-from-report",
    response_model=SuggestionGenerateFromReportResponse,
)
def suggestions_generate_from_report(
    payload: SuggestionGenerateFromReportRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> SuggestionGenerateFromReportResponse:
    require_action(session, "suggestions.generate")
    return generate_from_report(
        context=get_context(request),
        session=session,
        payload=payload,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/api/v1/suggestions", response_model=SuggestionListResponse)
def suggestions_list(
    request: Request,
    scope: str = Query(default="self", pattern="^(self|household)$"),
    limit: int = Query(default=20, ge=1, le=100),
    source_user_id: str | None = Query(default=None),
    session: dict[str, object] = Depends(current_session),
) -> SuggestionListResponse:
    require_action(session, "suggestions.read")
    return list_for_session(
        context=get_context(request),
        session=session,
        scope=scope,
        limit=limit,
        source_user_id=source_user_id,
    )


@router.get("/api/v1/suggestions/{suggestion_id}", response_model=SuggestionDetailResponse)
def suggestions_get(
    suggestion_id: str,
    request: Request,
    scope: str = Query(default="self", pattern="^(self|household)$"),
    session: dict[str, object] = Depends(current_session),
) -> SuggestionDetailResponse:
    require_action(session, "suggestions.read")
    return get_for_session(
        context=get_context(request),
        session=session,
        scope=scope,
        suggestion_id=suggestion_id,
    )
