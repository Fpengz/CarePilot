from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timezone
from uuid import uuid4

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.schemas import (
    SymptomCheckInEnvelopeResponse,
    SymptomCheckInListResponse,
    SymptomCheckInRequest,
    SymptomCheckInResponse,
    SymptomCountResponse,
    SymptomSafetyResponse,
    SymptomSummaryResponse,
)
from dietary_guardian.models.symptom import SymptomCheckIn, SymptomSafety
from dietary_guardian.safety.triage import evaluate_text_safety


def _to_response(item: SymptomCheckIn) -> SymptomCheckInResponse:
    return SymptomCheckInResponse(
        id=item.id,
        recorded_at=item.recorded_at,
        severity=item.severity,
        symptom_codes=list(item.symptom_codes),
        free_text=item.free_text,
        context=dict(item.context),
        safety=SymptomSafetyResponse.model_validate(item.safety.model_dump(mode="json")),
    )


def create_checkin_for_session(
    *,
    context: AppContext,
    user_id: str,
    payload: SymptomCheckInRequest,
) -> SymptomCheckInEnvelopeResponse:
    safety = evaluate_text_safety(payload.free_text or "")
    item = SymptomCheckIn(
        id=str(uuid4()),
        user_id=user_id,
        severity=payload.severity,
        symptom_codes=[code.strip() for code in payload.symptom_codes if code.strip()],
        free_text=payload.free_text,
        context=payload.context,
        safety=SymptomSafety(
            decision=safety.decision,
            reasons=list(safety.reasons),
            required_actions=list(safety.required_actions),
            redactions=list(safety.redactions),
        ),
    )
    saved = context.stores.symptoms.save_symptom_checkin(item)
    return SymptomCheckInEnvelopeResponse(item=_to_response(saved))


def list_checkins_for_session(
    *,
    context: AppContext,
    user_id: str,
    from_date: date | None,
    to_date: date | None,
    limit: int,
) -> SymptomCheckInListResponse:
    start_at = datetime.combine(from_date, time.min, tzinfo=timezone.utc) if from_date else None
    end_at = datetime.combine(to_date, time.max, tzinfo=timezone.utc) if to_date else None
    items = context.stores.symptoms.list_symptom_checkins(
        user_id=user_id,
        start_at=start_at,
        end_at=end_at,
        limit=limit,
    )
    return SymptomCheckInListResponse(items=[_to_response(item) for item in items])


def summarize_checkins_for_session(
    *,
    context: AppContext,
    user_id: str,
    from_date: date | None,
    to_date: date | None,
) -> SymptomSummaryResponse:
    start_at = datetime.combine(from_date, time.min, tzinfo=timezone.utc) if from_date else None
    end_at = datetime.combine(to_date, time.max, tzinfo=timezone.utc) if to_date else None
    items = context.stores.symptoms.list_symptom_checkins(
        user_id=user_id,
        start_at=start_at,
        end_at=end_at,
        limit=1000,
    )
    if not items:
        return SymptomSummaryResponse(
            total_count=0,
            average_severity=0.0,
            red_flag_count=0,
            top_symptoms=[],
            latest_recorded_at=None,
        )
    code_counts = Counter()
    for item in items:
        code_counts.update(item.symptom_codes)
    top = [
        SymptomCountResponse(code=code, count=count)
        for code, count in code_counts.most_common(5)
    ]
    red_flags = sum(1 for item in items if item.safety.decision == "escalate")
    latest = max((item.recorded_at for item in items), default=None)
    avg = sum(item.severity for item in items) / len(items)
    return SymptomSummaryResponse(
        total_count=len(items),
        average_severity=round(avg, 4),
        red_flag_count=red_flags,
        top_symptoms=top,
        latest_recorded_at=latest,
    )
