"""Tests for memory services."""

from dietary_guardian.domain.health.models import ClinicalProfileSnapshot
from dietary_guardian.domain.identity.models import (
    MedicalCondition,
    Medication,
    UserProfile,
)
from dietary_guardian.infrastructure.cache import (
    ClinicalSnapshotMemoryService,
    EventTimelineService,
    ProfileMemoryService,
)


def _user() -> UserProfile:
    return UserProfile(
        id="u1",
        name="Mr Tan",
        age=68,
        conditions=[MedicalCondition(name="Diabetes", severity="High")],
        medications=[Medication(name="Metformin", dosage="500mg")],
    )


def test_profile_memory_set_get() -> None:
    svc = ProfileMemoryService()
    user = _user()
    svc.put(user)

    stored = svc.get("u1")
    assert stored is not None
    assert stored.name == "Mr Tan"


def test_clinical_snapshot_memory_set_get() -> None:
    svc = ClinicalSnapshotMemoryService()
    snap = ClinicalProfileSnapshot(biomarkers={"ldl": 4.2}, risk_flags=["high_ldl"])
    svc.put("u1", snap)

    stored = svc.get("u1")
    assert stored is not None
    assert stored.biomarkers["ldl"] == 4.2


def test_event_timeline_append_list_and_filter() -> None:
    svc = EventTimelineService()
    svc.append(
        event_type="workflow_started",
        correlation_id="c1",
        payload={"a": 1},
        request_id="r1",
        user_id="u1",
    )
    svc.append(
        event_type="workflow_completed",
        correlation_id="c1",
        payload={"b": 2},
        request_id="r1",
        user_id="u1",
    )
    svc.append(
        event_type="workflow_started",
        correlation_id="c2",
        payload={"a": 9},
        request_id="r2",
        user_id="u2",
    )

    c1_events = svc.get_events(correlation_id="c1")
    assert len(c1_events) == 2
    assert [e.event_type for e in c1_events] == ["workflow_started", "workflow_completed"]

