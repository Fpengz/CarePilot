"""Shared context-building helpers for companion API endpoints."""

from __future__ import annotations

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.schemas import WorkflowResponse, WorkflowTimelineEventResponse
from dietary_guardian.application.auth.session_context import build_user_profile_from_session
from dietary_guardian.application.companion import CompanionStateInputs
from dietary_guardian.domain.health.models import ClinicalProfileSnapshot
from dietary_guardian.domain.reports import build_clinical_snapshot


def _subject_user_id(session: dict[str, object]) -> str:
    raw = session.get("subject_user_id")
    if isinstance(raw, str) and raw.strip():
        return raw
    return str(session["user_id"])



def _clinical_snapshot(context: AppContext, *, user_id: str) -> ClinicalProfileSnapshot | None:
    cached = context.clinical_memory.get(user_id)
    if cached is not None:
        return cached
    readings = context.stores.biomarkers.list_biomarker_readings(user_id)
    if not readings:
        return None
    snapshot = build_clinical_snapshot(readings)
    context.clinical_memory.put(user_id, snapshot)
    return snapshot



def _emotion_signal(context: AppContext, *, emotion_text: str | None) -> str | None:
    if not emotion_text:
        return None
    try:
        result = context.emotion_agent.infer_text(text=emotion_text)
    except Exception:
        lowered = emotion_text.lower()
        if any(term in lowered for term in ("stress", "stressed", "worried", "anxious")):
            return "anxious"
        if any(term in lowered for term in ("sad", "discouraged", "down", "frustrated")):
            return "sad"
        return None
    return str(result.emotion)



def load_companion_inputs(
    *,
    context: AppContext,
    session: dict[str, object],
    emotion_text: str | None = None,
) -> CompanionStateInputs:
    """Assemble the longitudinal inputs required by companion workflows."""
    subject_user_id = _subject_user_id(session)
    subject_session = dict(session)
    subject_session["user_id"] = subject_user_id
    user_profile = build_user_profile_from_session(subject_session, context.stores.profiles)
    health_profile = context.stores.profiles.get_health_profile(subject_user_id)
    meals = context.stores.meals.list_meal_records(subject_user_id)
    reminders = context.stores.reminders.list_reminder_events(subject_user_id)
    adherence_events = context.stores.medications.list_medication_adherence_events(user_id=subject_user_id)
    symptoms = context.stores.symptoms.list_symptom_checkins(user_id=subject_user_id, limit=200)
    readings = context.stores.biomarkers.list_biomarker_readings(subject_user_id)
    clinical_snapshot = _clinical_snapshot(context, user_id=subject_user_id)
    emotion_signal = _emotion_signal(context, emotion_text=emotion_text)
    return CompanionStateInputs(
        user_profile=user_profile,
        health_profile=health_profile,
        meals=meals,
        reminders=reminders,
        adherence_events=adherence_events,
        symptoms=symptoms,
        biomarker_readings=readings,
        clinical_snapshot=clinical_snapshot,
        emotion_signal=emotion_signal,
    )



def build_workflow_response(*, context: AppContext, correlation_id: str, request_id: str) -> WorkflowResponse:
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


__all__ = ["build_workflow_response", "load_companion_inputs"]
