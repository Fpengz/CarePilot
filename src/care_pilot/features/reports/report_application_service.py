"""
Orchestrate clinical report parsing workflows.

This module coordinates clinical report parsing and symptom-context enrichment.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from apps.api.carepilot_api.deps import AppContext

from care_pilot.core.contracts.api import (
    ReportParseRequest,
    ReportParseResponse,
    SymptomSummaryWindowResponse,
)
from care_pilot.features.companion.core.health.models import ReportInput
from care_pilot.features.reports.domain import build_clinical_snapshot, parse_report_input
from care_pilot.features.symptoms.symptom_service import summarize_checkins_for_session
from care_pilot.platform.observability.workflows.domain.models import WorkflowName


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
    context.stores.biomarkers.save_biomarker_readings(user_id, readings)
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

    context.event_timeline.append(
        event_type="workflow_started",
        workflow_name=WorkflowName.REPORT_PARSE.value,
        correlation_id=issued_correlation_id,
        request_id=issued_request_id,
        user_id=user_id,
        payload={"source": payload.source},
    )
    context.event_timeline.append(
        event_type="workflow_completed",
        workflow_name=WorkflowName.REPORT_PARSE.value,
        correlation_id=issued_correlation_id,
        request_id=issued_request_id,
        user_id=user_id,
        payload={
            "reading_count": len(readings),
            "symptom_checkin_count": symptom_summary.total_count,
            "red_flag_count": symptom_summary.red_flag_count,
            "window": {
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
                "limit": symptom_limit,
            },
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
