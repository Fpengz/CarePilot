from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.schemas import ReportParseRequest, ReportParseResponse, SymptomSummaryWindowResponse
from apps.api.dietary_api.services.symptoms import summarize_checkins_for_session
from dietary_guardian.models.report import ReportInput
from dietary_guardian.services.report_parser_service import build_clinical_snapshot, parse_report_input


def parse_report_for_session(
    *,
    context: AppContext,
    user_id: str,
    payload: ReportParseRequest,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> ReportParseResponse:
    issued_request_id = request_id or str(uuid4())
    issued_correlation_id = correlation_id or str(uuid4())

    report_input = ReportInput(source="pasted_text", text=payload.text)
    readings = parse_report_input(report_input)
    snapshot = build_clinical_snapshot(readings)
    context.repository.save_biomarker_readings(user_id, readings)
    context.clinical_memory.put(user_id, snapshot)

    end_date = date.today()
    start_date = end_date - timedelta(days=6)
    symptom_limit = 1000
    symptom_summary = summarize_checkins_for_session(
        context=context,
        user_id=user_id,
        from_date=start_date,
        to_date=end_date,
    )

    context.coordinator.run_report_parse_workflow(
        user_id=user_id,
        request_id=issued_request_id,
        correlation_id=issued_correlation_id,
        source=payload.source,
        reading_count=len(readings),
        symptom_checkin_count=symptom_summary.total_count,
        red_flag_count=symptom_summary.red_flag_count,
        window={
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "limit": symptom_limit,
        },
    )

    return ReportParseResponse(
        readings=[item.model_dump(mode="json") for item in readings],
        snapshot=snapshot.model_dump(mode="json"),
        symptom_summary=symptom_summary,
        symptom_window=SymptomSummaryWindowResponse(
            from_date=start_date,
            to_date=end_date,
            limit=symptom_limit,
        ),
    )
