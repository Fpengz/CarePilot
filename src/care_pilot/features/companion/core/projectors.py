"""Projection handlers for companion snapshot sections."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from care_pilot.core.events import DomainEvent
from care_pilot.features.companion.core.domain import PatientCaseSnapshot
from care_pilot.features.companion.core.projection_inputs import load_projection_inputs
from care_pilot.features.companion.core.snapshot import build_case_snapshot
from care_pilot.platform.cache import ClinicalSnapshotMemoryService
from care_pilot.platform.eventing.models import (
    EventProjectionHandler,
    OrderingScope,
    SnapshotSectionRecord,
)
from care_pilot.platform.persistence import AppStores
from care_pilot.platform.persistence.health_metrics import ChatHealthMetricsRepository

_SECTION_SCHEMA_VERSION = "v1"
_SECTION_PROJECTION_VERSION = "v1"


@dataclass(slots=True)
class CompanionSnapshotProjector(EventProjectionHandler):
    name: str
    event_types: Sequence[str]
    projection_section: str
    projection_version: str
    ordering_scope: OrderingScope
    stores: AppStores
    clinical_memory: ClinicalSnapshotMemoryService
    health_metrics: ChatHealthMetricsRepository

    def apply(self, event: DomainEvent) -> None:
        meta = event.payload.get("meta", {}) if isinstance(event.payload, dict) else {}
        user_id = meta.get("user_id")
        if not isinstance(user_id, str) or not user_id:
            return
        inputs = load_projection_inputs(
            stores=self.stores,
            clinical_memory=self.clinical_memory,
            health_metrics=self.health_metrics,
            user_id=user_id,
        )
        snapshot = build_case_snapshot(
            user_profile=inputs.user_profile,
            health_profile=inputs.health_profile,
            meals=inputs.meals,
            reminders=inputs.reminders,
            adherence_events=inputs.adherence_events,
            symptoms=inputs.symptoms,
            biomarker_readings=inputs.biomarker_readings,
            blood_pressure_readings=inputs.blood_pressure_readings,
            clinical_snapshot=inputs.clinical_snapshot,
        )
        sections = _build_snapshot_sections(snapshot, source_event_cursor=meta.get("event_id"))
        for section in sections:
            self.stores.eventing.upsert_snapshot_section(section)


def _build_snapshot_sections(
    snapshot: PatientCaseSnapshot,
    *,
    source_event_cursor: str | None,
) -> list[SnapshotSectionRecord]:
    now = datetime.now(UTC)
    sections: list[SnapshotSectionRecord] = []

    sections.append(
        SnapshotSectionRecord(
            user_id=snapshot.user_id,
            section_key="demographics",
            payload={
                "profile_name": snapshot.profile_name,
                "demographics": snapshot.demographics,
                "conditions": snapshot.conditions,
                "goals": snapshot.goals,
                "clinician_instructions": snapshot.clinician_instructions,
            },
            schema_version=_SECTION_SCHEMA_VERSION,
            projection_version=_SECTION_PROJECTION_VERSION,
            source_event_cursor=source_event_cursor,
            created_at=now,
            updated_at=now,
        )
    )

    sections.append(
        SnapshotSectionRecord(
            user_id=snapshot.user_id,
            section_key="medications_adherence",
            payload={
                "medications": snapshot.medications,
                "adherence_events": snapshot.adherence_events,
                "adherence_rate": snapshot.adherence_rate,
                "reminder_count": snapshot.reminder_count,
                "reminder_response_rate": snapshot.reminder_response_rate,
            },
            schema_version=_SECTION_SCHEMA_VERSION,
            projection_version=_SECTION_PROJECTION_VERSION,
            source_event_cursor=source_event_cursor,
            created_at=now,
            updated_at=now,
        )
    )

    sections.append(
        SnapshotSectionRecord(
            user_id=snapshot.user_id,
            section_key="meals_nutrition",
            payload={
                "meal_count": snapshot.meal_count,
                "latest_meal_name": snapshot.latest_meal_name,
                "meal_risk_streak": snapshot.meal_risk_streak,
                "recent_meals": snapshot.recent_meals,
            },
            schema_version=_SECTION_SCHEMA_VERSION,
            projection_version=_SECTION_PROJECTION_VERSION,
            source_event_cursor=source_event_cursor,
            created_at=now,
            updated_at=now,
        )
    )

    sections.append(
        SnapshotSectionRecord(
            user_id=snapshot.user_id,
            section_key="trends_vitals",
            payload={
                "biomarker_summary": snapshot.biomarker_summary,
                "blood_pressure_summary": snapshot.blood_pressure_summary.model_dump(mode="json")
                if snapshot.blood_pressure_summary
                else None,
                "active_risk_flags": snapshot.active_risk_flags,
                "trends": snapshot.trends,
            },
            schema_version=_SECTION_SCHEMA_VERSION,
            projection_version=_SECTION_PROJECTION_VERSION,
            source_event_cursor=source_event_cursor,
            created_at=now,
            updated_at=now,
        )
    )

    sections.append(
        SnapshotSectionRecord(
            user_id=snapshot.user_id,
            section_key="conversation_summary",
            payload={
                "current_conversation_turn": snapshot.current_conversation_turn,
                "pending_tasks": snapshot.pending_tasks,
                "unresolved_questions": snapshot.unresolved_questions,
                "last_interaction_at": snapshot.last_interaction_at.isoformat()
                if snapshot.last_interaction_at
                else None,
                "recent_symptoms": snapshot.recent_symptoms,
                "recent_emotion_markers": snapshot.recent_emotion_markers,
                "symptom_count": snapshot.symptom_count,
                "average_symptom_severity": snapshot.average_symptom_severity,
            },
            schema_version=_SECTION_SCHEMA_VERSION,
            projection_version=_SECTION_PROJECTION_VERSION,
            source_event_cursor=source_event_cursor,
            created_at=now,
            updated_at=now,
        )
    )

    return sections


__all__ = ["CompanionSnapshotProjector"]
