"""
Build companion context used by API services.

This module assembles clinical snapshots, evidence, and session context
required to drive companion orchestration responses.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Literal, cast
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from apps.api.carepilot_api.deps import AppContext
from care_pilot.core.contracts.api import (
    BloodPressureChartResponse,
    BloodPressureSummaryEnvelopeResponse,
    BloodPressureSummaryResponse,
    ClinicianDigestEnvelopeResponse,
    ClinicianDigestResponse,
    CompanionCarePlanResponse,
    CompanionEngagementResponse,
    CompanionInteractionInfoResponse,
    CompanionInteractionRequest,
    CompanionInteractionResponse,
    CompanionSnapshotResponse,
    CompanionTodayResponse,
    ImpactSummaryPayloadResponse,
    ImpactSummaryResponse,
    WorkflowResponse,
    WorkflowTimelineEventResponse,
)
from care_pilot.features.companion.chat.search_adapter import SearchAgent
from care_pilot.features.companion.core.companion_core_service import (
    CompanionStateInputs,
    build_companion_today_bundle,
    run_companion_interaction,
)
from care_pilot.features.companion.core.domain.models import CompanionInteraction
from care_pilot.features.companion.core.evidence.ports import EvidenceRetrievalPort
from care_pilot.features.companion.core.health.blood_pressure import (
    build_bp_chart_points,
    summarize_blood_pressure,
)
from care_pilot.features.companion.core.health.models import (
    BiomarkerReading,
    BloodPressureReading,
    ClinicalProfileSnapshot,
    HealthProfileRecord,
    MedicationAdherenceEvent,
    SymptomCheckIn,
)
from care_pilot.features.meals.domain.recognition import MealRecognitionRecord
from care_pilot.features.profiles.domain.models import UserProfile
from care_pilot.features.reminders.domain.models import ReminderEvent
from care_pilot.features.reports.domain import build_clinical_snapshot
from care_pilot.platform.auth.session_context import build_user_profile_from_session
from care_pilot.platform.persistence.evidence import SearchEvidenceRetriever
from care_pilot.platform.persistence.health_metrics import ChatHealthMetricsRepository

_EVIDENCE_RETRIEVER: EvidenceRetrievalPort = SearchEvidenceRetriever(
    search_agent=SearchAgent(max_results=3, timeout=6)
)
_HEALTH_METRICS = ChatHealthMetricsRepository()


def _companion_today_cache_key(user_id: str) -> str:
    return f"companion.today.v1:{user_id}"


def _resolve_bp_range(
    *, range_key: str, from_date: date | None, to_date: date | None, timezone_name: str
) -> tuple[date, date, str]:
    if range_key == "custom":
        if from_date is None or to_date is None:
            raise ValueError("custom range requires from and to")
        if from_date > to_date:
            raise ValueError("from must be before to")
        bucket = "day" if (to_date - from_date).days <= 30 else "week"
        return from_date, to_date, bucket
    presets: dict[str, int] = {"7d": 7, "30d": 30, "3m": 90, "1y": 365}
    days = presets.get(range_key, 30)
    today = datetime.now(ZoneInfo(timezone_name)).date()
    start = today - timedelta(days=days - 1)
    bucket = "day" if days <= 30 else "week"
    return start, today, bucket


def _subject_user_id(session: dict[str, object]) -> str:
    raw = session.get("subject_user_id")
    if isinstance(raw, str) and raw.strip():
        return raw
    return str(session["user_id"])


def _clinical_snapshot(
    context: AppContext, *, user_id: str, readings: list[BiomarkerReading]
) -> ClinicalProfileSnapshot | None:
    cached = context.clinical_memory.get(user_id)
    if cached is not None:
        return cached
    if not readings:
        return None
    snapshot = build_clinical_snapshot(readings)
    context.clinical_memory.put(user_id, snapshot)
    return snapshot


async def _emotion_signal(context: AppContext, *, emotion_text: str | None) -> str | None:
    if not emotion_text:
        return None
    try:
        result = await context.emotion_agent.infer_text(text=emotion_text)
    except Exception:
        lowered = emotion_text.lower()
        if any(term in lowered for term in ("stress", "stressed", "worried", "anxious")):
            return "anxious"
        if any(term in lowered for term in ("sad", "discouraged", "down", "frustrated")):
            return "sad"
        return None
    return str(result.final_emotion)


async def load_companion_inputs(
    *,
    context: AppContext,
    session: dict[str, object],
    emotion_text: str | None = None,
) -> CompanionStateInputs:
    """Assemble the longitudinal inputs required by companion workflows."""
    subject_user_id = _subject_user_id(session)
    subject_session = dict(session)
    subject_session["user_id"] = subject_user_id

    # 1. Start all I/O bound queries in parallel
    results = await asyncio.gather(
        asyncio.to_thread(build_user_profile_from_session, subject_session, context.stores.profiles),
        asyncio.to_thread(context.stores.profiles.get_health_profile, subject_user_id),
        asyncio.to_thread(context.stores.meals.list_meal_records, subject_user_id),
        asyncio.to_thread(context.stores.reminders.list_reminder_events, subject_user_id),
        asyncio.to_thread(
            context.stores.medications.list_medication_adherence_events, user_id=subject_user_id
        ),
        asyncio.to_thread(
            context.stores.symptoms.list_symptom_checkins, user_id=subject_user_id, limit=200
        ),
        asyncio.to_thread(context.stores.biomarkers.list_biomarker_readings, subject_user_id),
        asyncio.to_thread(_HEALTH_METRICS.list_blood_pressure_readings, user_id=subject_user_id),
        _emotion_signal(context, emotion_text=emotion_text),
    )

    (
        user_profile,
        health_profile,
        meals,
        reminders,
        adherence_events,
        symptoms,
        readings,
        bp_readings,
        emotion_signal,
    ) = cast(
        tuple[
            UserProfile,
            HealthProfileRecord | None,
            list[MealRecognitionRecord],
            list[ReminderEvent],
            list[MedicationAdherenceEvent],
            list[SymptomCheckIn],
            list[BiomarkerReading],
            list[BloodPressureReading],
            str | None,
        ],
        results,
    )

    # 2. Derive clinical snapshot (synchronous/fast once readings are here)
    clinical_snapshot = _clinical_snapshot(context, user_id=subject_user_id, readings=readings)

    return CompanionStateInputs(
        user_profile=user_profile,
        health_profile=health_profile,
        meals=meals,
        reminders=reminders,
        adherence_events=adherence_events,
        symptoms=symptoms,
        biomarker_readings=readings,
        blood_pressure_readings=bp_readings,
        clinical_snapshot=clinical_snapshot,
        emotion_signal=emotion_signal,
    )


def build_workflow_response(
    *, context: AppContext, correlation_id: str, request_id: str
) -> WorkflowResponse:
    """Render the recorded companion workflow timeline into the API response shape."""
    timeline = context.event_timeline.get_events(correlation_id=correlation_id)
    return WorkflowResponse(
        workflow_name="companion_interaction",
        request_id=request_id,
        correlation_id=correlation_id,
        replayed=False,
        timeline_events=[
            WorkflowTimelineEventResponse.model_validate(item.model_dump(mode="json"))
            for item in timeline
        ],
    )


async def get_companion_today(
    *, context: AppContext, session: dict[str, object]
) -> CompanionTodayResponse:
    """Build the current companion summary for the active session."""
    subject_user_id = _subject_user_id(session)
    cached = context.cache_store.get_json(_companion_today_cache_key(subject_user_id))
    if cached is not None:
        return CompanionTodayResponse.model_validate(cached)
    inputs = await load_companion_inputs(context=context, session=session)
    snapshot, engagement, _, _, impact, result = build_companion_today_bundle(
        inputs=inputs,
        evidence_retriever=_EVIDENCE_RETRIEVER,
        eventing_store=context.stores.eventing,
    )
    response = CompanionTodayResponse(
        snapshot=CompanionSnapshotResponse.model_validate(snapshot.model_dump(mode="json")),
        engagement=CompanionEngagementResponse.model_validate(engagement.model_dump(mode="json")),
        care_plan=CompanionCarePlanResponse.model_validate(
            result.care_plan.model_dump(mode="json")
        ),
        impact=ImpactSummaryPayloadResponse.model_validate(impact.model_dump(mode="json")),
    )
    context.cache_store.set_json(
        _companion_today_cache_key(subject_user_id),
        response.model_dump(mode="json"),
        ttl_seconds=int(context.settings.storage.redis_default_ttl_seconds),
    )
    return response


async def get_blood_pressure_summary(
    *, context: AppContext, session: dict[str, object]
) -> BloodPressureSummaryEnvelopeResponse:
    subject_user_id = _subject_user_id(session)
    subject_session = dict(session)
    subject_session["user_id"] = subject_user_id
    user_profile = build_user_profile_from_session(subject_session, context.stores.profiles)
    health_profile = context.stores.profiles.get_health_profile(subject_user_id)
    condition_names = [item.name for item in user_profile.conditions]
    if health_profile is not None and not condition_names:
        condition_names = [item.name for item in health_profile.conditions]
    readings = _HEALTH_METRICS.list_blood_pressure_readings(user_id=subject_user_id)
    summary = summarize_blood_pressure(readings, conditions=condition_names)
    return BloodPressureSummaryEnvelopeResponse(
        user_id=subject_user_id,
        summary=BloodPressureSummaryResponse.model_validate(summary.model_dump(mode="json"))
        if summary is not None
        else None,
        generated_at=datetime.now(UTC),
    )


async def get_blood_pressure_chart(
    *,
    context: AppContext,
    session: dict[str, object],
    range_key: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> BloodPressureChartResponse:
    subject_user_id = _subject_user_id(session)
    timezone_name = context.settings.app.timezone
    start, end, bucket = _resolve_bp_range(
        range_key=range_key, from_date=from_date, to_date=to_date, timezone_name=timezone_name
    )
    readings = _HEALTH_METRICS.list_blood_pressure_readings(user_id=subject_user_id)
    points = build_bp_chart_points(
        readings, start=start, end=end, timezone_name=timezone_name, bucket=bucket
    )
    return BloodPressureChartResponse(
        user_id=subject_user_id,
        range=cast(
            Literal["7d", "30d", "3m", "1y", "custom"],
            range_key if range_key in {"7d", "30d", "3m", "1y", "custom"} else "30d",
        ),
        generated_at=datetime.now(UTC),
        points=points,  # type: ignore[arg-type]
    )


async def handle_companion_interaction(
    *,
    context: AppContext,
    session: dict[str, object],
    payload: CompanionInteractionRequest,
    request_id: str,
    correlation_id: str,
) -> CompanionInteractionResponse:
    """Run a single companion interaction and return the assembled care outputs."""
    inputs = await load_companion_inputs(
        context=context,
        session=session,
        emotion_text=payload.emotion_text,
    )
    context.event_timeline.append(
        event_type="workflow_started",
        workflow_name="companion_interaction",
        request_id=request_id,
        correlation_id=correlation_id,
        user_id=str(session["user_id"]),
        payload={
            "interaction_type": payload.interaction_type,
            "has_emotion_text": bool(payload.emotion_text),
        },
    )
    interaction = CompanionInteraction(
        interaction_type=payload.interaction_type,
        message=payload.message,
        request_id=request_id,
        correlation_id=correlation_id,
        emotion_signal=inputs.emotion_signal,
    )
    result = run_companion_interaction(
        interaction=interaction,
        inputs=inputs,
        evidence_retriever=_EVIDENCE_RETRIEVER,
        eventing_store=context.stores.eventing,
    )
    context.event_timeline.append(
        event_type="workflow_completed",
        workflow_name="companion_interaction",
        request_id=request_id,
        correlation_id=correlation_id,
        user_id=str(session["user_id"]),
        payload={
            "risk_level": result.engagement.risk_level,
            "recommended_mode": result.engagement.recommended_mode,
        },
    )
    return CompanionInteractionResponse(
        interaction=CompanionInteractionInfoResponse.model_validate(
            interaction.model_dump(mode="json")
        ),
        snapshot=CompanionSnapshotResponse.model_validate(result.snapshot.model_dump(mode="json")),
        engagement=CompanionEngagementResponse.model_validate(
            result.engagement.model_dump(mode="json")
        ),
        care_plan=CompanionCarePlanResponse.model_validate(
            result.care_plan.model_dump(mode="json")
        ),
        clinician_digest_preview=ClinicianDigestResponse.model_validate(
            result.clinician_digest_preview.model_dump(mode="json")
        ),
        impact=ImpactSummaryPayloadResponse.model_validate(result.impact.model_dump(mode="json")),
        workflow=build_workflow_response(
            context=context,
            correlation_id=correlation_id,
            request_id=request_id,
        ),
    )


async def get_clinician_digest(
    *, context: AppContext, session: dict[str, object]
) -> ClinicianDigestEnvelopeResponse:
    """Build the clinician-digest projection for the active session."""
    inputs = await load_companion_inputs(context=context, session=session)
    _, _, _, digest, _, _ = build_companion_today_bundle(
        inputs=inputs,
        evidence_retriever=_EVIDENCE_RETRIEVER,
        eventing_store=context.stores.eventing,
    )
    return ClinicianDigestEnvelopeResponse(
        digest=ClinicianDigestResponse.model_validate(digest.model_dump(mode="json"))
    )


async def get_impact_summary(*, context: AppContext, session: dict[str, object]) -> ImpactSummaryResponse:
    """Build the impact-summary projection for the active session."""
    inputs = await load_companion_inputs(context=context, session=session)
    _, _, _, _, impact, _ = build_companion_today_bundle(
        inputs=inputs,
        evidence_retriever=_EVIDENCE_RETRIEVER,
        eventing_store=context.stores.eventing,
    )
    return ImpactSummaryResponse(
        summary=ImpactSummaryPayloadResponse.model_validate(impact.model_dump(mode="json"))
    )


__all__ = [
    "build_workflow_response",
    "get_clinician_digest",
    "get_companion_today",
    "get_impact_summary",
    "handle_companion_interaction",
    "load_companion_inputs",
]
