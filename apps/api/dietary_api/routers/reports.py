from fastapi import APIRouter, Depends, Request

from dietary_guardian.models.report import ReportInput
from dietary_guardian.services.report_parser_service import build_clinical_snapshot, parse_report_input

from ..routes_shared import current_session, get_context, require_scopes
from ..schemas import ReportParseRequest, ReportParseResponse

router = APIRouter(tags=["reports"])


@router.post("/api/v1/reports/parse", response_model=ReportParseResponse)
def reports_parse(
    payload: ReportParseRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReportParseResponse:
    require_scopes(session, {"report:write"})
    context = get_context(request)
    report_input = ReportInput(source="pasted_text", text=payload.text)
    readings = parse_report_input(report_input)
    snapshot = build_clinical_snapshot(readings)
    user_id = str(session["user_id"])
    context.repository.save_biomarker_readings(user_id, readings)
    context.clinical_memory.put(user_id, snapshot)
    return ReportParseResponse(
        readings=[item.model_dump(mode="json") for item in readings],
        snapshot=snapshot.model_dump(mode="json"),
    )
