from __future__ import annotations

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.schemas import ReportParseRequest, ReportParseResponse
from dietary_guardian.models.report import ReportInput
from dietary_guardian.services.report_parser_service import build_clinical_snapshot, parse_report_input


def parse_report_for_session(
    *,
    context: AppContext,
    user_id: str,
    payload: ReportParseRequest,
) -> ReportParseResponse:
    report_input = ReportInput(source="pasted_text", text=payload.text)
    readings = parse_report_input(report_input)
    snapshot = build_clinical_snapshot(readings)
    context.repository.save_biomarker_readings(user_id, readings)
    context.clinical_memory.put(user_id, snapshot)
    return ReportParseResponse(
        readings=[item.model_dump(mode="json") for item in readings],
        snapshot=snapshot.model_dump(mode="json"),
    )
