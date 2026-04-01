"""Build companion inputs for projection handlers."""

from __future__ import annotations

from care_pilot.features.companion.core.core_service import CompanionStateInputs
from care_pilot.features.companion.core.health.models import ClinicalProfileSnapshot
from care_pilot.features.profiles.domain.health_profile import resolve_user_profile
from care_pilot.features.reports.domain import build_clinical_snapshot
from care_pilot.platform.cache import ClinicalSnapshotMemoryService
from care_pilot.platform.persistence import AppStores
from care_pilot.platform.persistence.health_metrics import ChatHealthMetricsRepository

_DEFAULT_SESSION = {
    "display_name": "Patient",
    "account_role": "member",
}


def _clinical_snapshot(
    *,
    clinical_memory: ClinicalSnapshotMemoryService,
    user_id: str,
    readings: list,
) -> ClinicalProfileSnapshot | None:
    cached = clinical_memory.get(user_id)
    if cached is not None:
        return cached
    if not readings:
        return None
    snapshot = build_clinical_snapshot(readings)
    clinical_memory.put(user_id, snapshot)
    return snapshot


def load_projection_inputs(
    *,
    stores: AppStores,
    clinical_memory: ClinicalSnapshotMemoryService,
    health_metrics: ChatHealthMetricsRepository,
    user_id: str,
) -> CompanionStateInputs:
    session = {"user_id": user_id, **_DEFAULT_SESSION}
    health_profile, user_profile = resolve_user_profile(stores.profiles, session)
    meals = stores.meals.list_meal_records(user_id)
    reminders = stores.reminders.list_reminder_events(user_id)
    adherence_events = stores.medications.list_medication_adherence_events(user_id=user_id)
    symptoms = stores.symptoms.list_symptom_checkins(user_id=user_id, limit=200)
    readings = stores.biomarkers.list_biomarker_readings(user_id)
    bp_readings = health_metrics.list_blood_pressure_readings(user_id=user_id)
    clinical_snapshot = _clinical_snapshot(
        clinical_memory=clinical_memory,
        user_id=user_id,
        readings=readings,
    )
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
        emotion_signal=None,
    )
