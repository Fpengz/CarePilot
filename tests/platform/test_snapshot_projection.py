from __future__ import annotations

from datetime import UTC, datetime

from care_pilot.features.companion.core.health.models import HealthProfileRecord
from care_pilot.features.companion.core.snapshot import (
    build_case_snapshot_prefer_projection,
    load_snapshot_from_sections,
)
from care_pilot.features.profiles.domain.models import UserProfile
from care_pilot.platform.eventing import SnapshotSectionRecord


class _SectionStore:
    def __init__(self, sections: list[SnapshotSectionRecord]) -> None:
        self._sections = sections

    def list_snapshot_sections(self, *, user_id: str):  # noqa: ANN001
        return [section for section in self._sections if section.user_id == user_id]


def _base_sections(user_id: str) -> list[SnapshotSectionRecord]:
    now = datetime.now(UTC)
    return [
        SnapshotSectionRecord(
            user_id=user_id,
            section_key="demographics",
            payload={
                "profile_name": "Projected",
                "demographics": {"age": 40},
                "conditions": [],
                "goals": [],
                "clinician_instructions": [],
            },
            schema_version="v1",
            projection_version="v1",
            created_at=now,
            updated_at=now,
        ),
        SnapshotSectionRecord(
            user_id=user_id,
            section_key="medications_adherence",
            payload={
                "medications": [],
                "adherence_events": 0,
                "adherence_rate": None,
                "reminder_count": 0,
                "reminder_response_rate": 0.0,
            },
            schema_version="v1",
            projection_version="v1",
            created_at=now,
            updated_at=now,
        ),
        SnapshotSectionRecord(
            user_id=user_id,
            section_key="meals_nutrition",
            payload={
                "meal_count": 0,
                "latest_meal_name": None,
                "meal_risk_streak": 0,
                "recent_meals": [],
            },
            schema_version="v1",
            projection_version="v1",
            created_at=now,
            updated_at=now,
        ),
        SnapshotSectionRecord(
            user_id=user_id,
            section_key="trends_vitals",
            payload={
                "biomarker_summary": {},
                "blood_pressure_summary": None,
                "active_risk_flags": [],
                "trends": {},
            },
            schema_version="v1",
            projection_version="v1",
            created_at=now,
            updated_at=now,
        ),
        SnapshotSectionRecord(
            user_id=user_id,
            section_key="conversation_summary",
            payload={
                "current_conversation_turn": 0,
                "pending_tasks": [],
                "unresolved_questions": [],
                "last_interaction_at": None,
                "recent_symptoms": [],
                "recent_emotion_markers": [],
            },
            schema_version="v1",
            projection_version="v1",
            created_at=now,
            updated_at=now,
        ),
    ]


def test_load_snapshot_from_sections_requires_all_sections() -> None:
    user_id = "user-1"
    sections = _base_sections(user_id)
    store = _SectionStore(sections[:-1])
    snapshot = load_snapshot_from_sections(user_id=user_id, eventing_store=store)
    assert snapshot is None


def test_build_snapshot_prefers_projection() -> None:
    user_id = "user-2"
    store = _SectionStore(_base_sections(user_id))
    profile = UserProfile(
        id=user_id,
        name="Fallback",
        age=50,
        conditions=[],
        medications=[],
    )
    health_profile = HealthProfileRecord(user_id=user_id)
    snapshot = build_case_snapshot_prefer_projection(
        user_id=user_id,
        eventing_store=store,
        user_profile=profile,
        health_profile=health_profile,
        meals=[],
        reminders=[],
        adherence_events=[],
        symptoms=[],
        biomarker_readings=[],
        blood_pressure_readings=[],
        clinical_snapshot=None,
    )
    assert snapshot.profile_name == "Projected"
