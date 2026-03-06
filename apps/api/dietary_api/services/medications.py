from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import uuid4

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    MedicationAdherenceEventCreateRequest,
    MedicationAdherenceEventEnvelopeResponse,
    MedicationAdherenceEventResponse,
    MedicationAdherenceMetricsResponse,
    MedicationAdherenceTotalsResponse,
    MedicationRegimenCreateRequest,
    MedicationRegimenDeleteResponse,
    MedicationRegimenEnvelopeResponse,
    MedicationRegimenListResponse,
    MedicationRegimenPatchRequest,
    MedicationRegimenResponse,
)
from dietary_guardian.models.medication import MedicationRegimen
from dietary_guardian.models.medication_tracking import MedicationAdherenceEvent, MedicationAdherenceMetrics


def _parse_hhmm(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    hh, mm = raw.split(":", 1)
    hour = int(hh)
    minute = int(mm)
    time(hour=hour, minute=minute)
    return f"{hour:02d}:{minute:02d}"


def _to_regimen_response(regimen: MedicationRegimen) -> MedicationRegimenResponse:
    return MedicationRegimenResponse.model_validate(regimen.model_dump(mode="json"))


def _to_adherence_response(event: MedicationAdherenceEvent) -> MedicationAdherenceEventResponse:
    return MedicationAdherenceEventResponse.model_validate(event.model_dump(mode="json"))


def list_regimens_for_session(*, context: AppContext, user_id: str) -> MedicationRegimenListResponse:
    items = context.repository.list_medication_regimens(user_id)
    return MedicationRegimenListResponse(items=[_to_regimen_response(item) for item in items])


def create_regimen_for_session(
    *,
    context: AppContext,
    user_id: str,
    payload: MedicationRegimenCreateRequest,
) -> MedicationRegimenEnvelopeResponse:
    fixed_time = _parse_hhmm(payload.fixed_time)
    if payload.timing_type == "fixed_time" and fixed_time is None:
        raise build_api_error(
            status_code=400,
            code="medications.invalid_fixed_time",
            message="fixed_time is required for fixed_time regimens",
        )
    regimen = MedicationRegimen(
        id=str(uuid4()),
        user_id=user_id,
        medication_name=payload.medication_name.strip(),
        dosage_text=payload.dosage_text.strip(),
        timing_type=payload.timing_type,
        offset_minutes=payload.offset_minutes,
        slot_scope=list(payload.slot_scope),
        fixed_time=fixed_time,
        max_daily_doses=payload.max_daily_doses,
        active=payload.active,
    )
    context.repository.save_medication_regimen(regimen)
    return MedicationRegimenEnvelopeResponse(regimen=_to_regimen_response(regimen))


def patch_regimen_for_session(
    *,
    context: AppContext,
    user_id: str,
    regimen_id: str,
    payload: MedicationRegimenPatchRequest,
) -> MedicationRegimenEnvelopeResponse:
    existing = context.repository.get_medication_regimen(user_id=user_id, regimen_id=regimen_id)
    if existing is None:
        raise build_api_error(status_code=404, code="medications.not_found", message="medication regimen not found")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise build_api_error(status_code=400, code="medications.no_changes", message="no medication changes requested")
    if "fixed_time" in updates:
        updates["fixed_time"] = _parse_hhmm(payload.fixed_time)
    next_payload = existing.model_dump(mode="json")
    next_payload.update(updates)
    if next_payload.get("timing_type") == "fixed_time" and not next_payload.get("fixed_time"):
        raise build_api_error(
            status_code=400,
            code="medications.invalid_fixed_time",
            message="fixed_time is required for fixed_time regimens",
        )
    updated = MedicationRegimen.model_validate(next_payload)
    context.repository.save_medication_regimen(updated)
    return MedicationRegimenEnvelopeResponse(regimen=_to_regimen_response(updated))


def delete_regimen_for_session(*, context: AppContext, user_id: str, regimen_id: str) -> MedicationRegimenDeleteResponse:
    deleted = context.repository.delete_medication_regimen(user_id=user_id, regimen_id=regimen_id)
    return MedicationRegimenDeleteResponse(deleted=deleted)


def record_adherence_for_session(
    *,
    context: AppContext,
    user_id: str,
    payload: MedicationAdherenceEventCreateRequest,
) -> MedicationAdherenceEventEnvelopeResponse:
    regimen = context.repository.get_medication_regimen(user_id=user_id, regimen_id=payload.regimen_id)
    if regimen is None:
        raise build_api_error(status_code=404, code="medications.not_found", message="medication regimen not found")
    event = MedicationAdherenceEvent(
        id=str(uuid4()),
        user_id=user_id,
        regimen_id=payload.regimen_id,
        reminder_id=payload.reminder_id,
        status=payload.status,
        scheduled_at=payload.scheduled_at,
        taken_at=payload.taken_at,
        source=payload.source,
        metadata=payload.metadata,
    )
    saved = context.repository.save_medication_adherence_event(event)
    return MedicationAdherenceEventEnvelopeResponse(event=_to_adherence_response(saved))


def adherence_metrics_for_session(
    *,
    context: AppContext,
    user_id: str,
    from_date: date | None,
    to_date: date | None,
) -> MedicationAdherenceMetricsResponse:
    start_at = datetime.combine(from_date, time.min, tzinfo=timezone.utc) if from_date else None
    end_at = datetime.combine(to_date, time.max, tzinfo=timezone.utc) if to_date else None
    events = context.repository.list_medication_adherence_events(
        user_id=user_id,
        start_at=start_at,
        end_at=end_at,
    )
    taken = sum(1 for item in events if item.status == "taken")
    missed = sum(1 for item in events if item.status == "missed")
    skipped = sum(1 for item in events if item.status == "skipped")
    totals = MedicationAdherenceMetrics(
        events=len(events),
        taken=taken,
        missed=missed,
        skipped=skipped,
        adherence_rate=(taken / len(events)) if events else 0.0,
    )
    return MedicationAdherenceMetricsResponse(
        totals=MedicationAdherenceTotalsResponse.model_validate(totals.model_dump(mode="json")),
        events=[_to_adherence_response(item) for item in events],
    )
