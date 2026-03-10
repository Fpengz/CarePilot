"""API router for reports endpoints."""

from fastapi import APIRouter, Depends, Request

from ..routes_shared import current_session, get_context, require_action
from ..schemas import ReportParseRequest, ReportParseResponse
from dietary_guardian.application.reports.use_cases import parse_report_for_session

router = APIRouter(tags=["reports"])


@router.post("/api/v1/reports/parse", response_model=ReportParseResponse)
def reports_parse(
    payload: ReportParseRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReportParseResponse:
    require_action(session, "reports.parse")
    return parse_report_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        payload=payload,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
