from datetime import datetime, timezone

from dietary_guardian.models.meal import (
    GlycemicIndexLevel,
    Ingredient,
    LocalizationDetails,
    MealState,
    Nutrition,
    PortionSize,
    VisionResult,
)
from dietary_guardian.models.user import MedicalCondition, Medication, UserProfile
from dietary_guardian.services.memory_services import (
    ClinicalSnapshotMemoryService,
    EventTimelineService,
    ProfileMemoryService,
)
from dietary_guardian.services.platform_tools import build_platform_tool_registry
from dietary_guardian.infrastructure.persistence import SQLiteRepository
from dietary_guardian.services.workflow_coordinator import WorkflowCoordinator
from dietary_guardian.models.contracts import CaptureEnvelope


def _user() -> UserProfile:
    return UserProfile(
        id="u1",
        name="Mr Tan",
        age=68,
        conditions=[MedicalCondition(name="Diabetes", severity="High")],
        medications=[Medication(name="Metformin", dosage="500mg")],
        profile_mode="caregiver",
    )


def _vision_result(needs_manual_review: bool = False) -> VisionResult:
    return VisionResult(
        primary_state=MealState(
            dish_name="Laksa",
            confidence_score=0.95 if not needs_manual_review else 0.6,
            identification_method="AI_Flash",
            ingredients=[Ingredient(name="Noodles")],
            nutrition=Nutrition(
                calories=500,
                carbs_g=50,
                sugar_g=5,
                protein_g=20,
                fat_g=20,
                sodium_mg=1200,
                fiber_g=2,
            ),
            portion_size=PortionSize.STANDARD,
            glycemic_index_estimate=GlycemicIndexLevel.HIGH,
            localization=LocalizationDetails(dialect_name="Malay", variant="Singapore"),
        ),
        raw_ai_output="Processed via ollama:qwen3-vl:4b",
        needs_manual_review=needs_manual_review,
        processing_latency_ms=1234.0,
        model_version="qwen3-vl:4b",
    )


def _capture() -> CaptureEnvelope:
    return CaptureEnvelope(
        capture_id="cap1",
        request_id="req1",
        correlation_id="corr1",
        user_id="u1",
        source="camera",
        modality="image",
        mime_type="image/jpeg",
        filename="cam.jpg",
        content_sha256="abc",
        metadata={"multi_item_count": "1"},
        captured_at=datetime.now(timezone.utc),
    )


def test_meal_workflow_emits_typed_output_and_handoff(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "coordinator.db"))
    timeline = EventTimelineService()
    coordinator = WorkflowCoordinator(
        tool_registry=build_platform_tool_registry(repo),
        profile_memory=ProfileMemoryService(),
        clinical_memory=ClinicalSnapshotMemoryService(),
        event_timeline=timeline,
    )
    user = _user()

    result = coordinator.run_meal_analysis_workflow(
        capture=_capture(),
        vision_result=_vision_result(needs_manual_review=True),
        user_profile=user,
        meal_record_id="meal-rec-123",
    )

    assert result.workflow_name == "meal_analysis"
    assert result.output_envelope is not None
    assert result.output_envelope.domain_decision.decision_type == "meal_analysis"
    assert result.output_envelope.correlation_id == "corr1"
    assert result.output_envelope.audit_record.correlation_id == "corr1"
    assert result.output_envelope.trace.correlation_id == "corr1"
    assert result.handoffs
    assert result.handoffs[0].to_agent == "clinical_reasoning_agent"
    events = timeline.list(correlation_id="corr1")
    assert len(events) >= 2
    completed = [event for event in events if event.event_type == "workflow_completed"][-1]
    assert completed.payload["meal_record_id"] == "meal-rec-123"
    assert completed.payload["confidence"] == 0.6
    assert completed.payload["estimated_calories"] == 500.0
    assert completed.payload["model_version"] == "qwen3-vl:4b"
    started = [event for event in events if event.event_type == "workflow_started"][-1]
    assert started.payload["capture_source"] == "camera"
    assert started.payload["meal_filename"] == "cam.jpg"


def test_alert_workflow_uses_tool_registry_and_records_timeline(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    timeline = EventTimelineService()
    coordinator = WorkflowCoordinator(
        tool_registry=build_platform_tool_registry(repo),
        profile_memory=ProfileMemoryService(),
        clinical_memory=ClinicalSnapshotMemoryService(),
        event_timeline=timeline,
    )
    user = _user()

    result = coordinator.run_alert_workflow(
        user_profile=user,
        alert_type="manual_test_alert",
        severity="warning",
        message="hello",
        destinations=["in_app"],
        account_role="admin",
        scopes=["alert:trigger"],
    )

    assert result.workflow_name == "alert_only"
    assert result.tool_results
    assert result.tool_results[0].success is True
    assert timeline.list(correlation_id=result.correlation_id)


def test_alert_workflow_propagates_environment_to_tool_context(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    timeline = EventTimelineService()
    coordinator = WorkflowCoordinator(
        tool_registry=build_platform_tool_registry(repo),
        profile_memory=ProfileMemoryService(),
        clinical_memory=ClinicalSnapshotMemoryService(),
        event_timeline=timeline,
    )

    result = coordinator.run_alert_workflow(
        user_profile=_user(),
        alert_type="manual_test_alert",
        severity="warning",
        message="hello",
        destinations=["in_app"],
        account_role="admin",
        scopes=["alert:trigger"],
        environment="prod",
    )

    assert result.tool_results[0].success is True
    assert result.tool_results[0].trace_metadata["environment"] == "prod"


def test_replay_returns_timeline_without_new_side_effects(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    timeline = EventTimelineService()
    registry = build_platform_tool_registry(repo)
    coordinator = WorkflowCoordinator(
        tool_registry=registry,
        profile_memory=ProfileMemoryService(),
        clinical_memory=ClinicalSnapshotMemoryService(),
        event_timeline=timeline,
    )
    user = _user()
    before = registry.snapshot_metrics().get("trigger_alert", {}).get("calls", 0)
    live = coordinator.run_alert_workflow(
        user_profile=user,
        alert_type="manual_test_alert",
        severity="warning",
        message="hello",
        destinations=["in_app"],
        account_role="admin",
        scopes=["alert:trigger"],
    )
    after_live = registry.snapshot_metrics()["trigger_alert"]["calls"]

    replay = coordinator.replay_workflow(live.correlation_id)
    after_replay = registry.snapshot_metrics()["trigger_alert"]["calls"]

    assert after_live == before + 1
    assert after_replay == after_live
    assert replay.workflow_name == "replay"
    assert replay.replayed is True
    assert replay.timeline_events


def test_replay_survives_restart_with_durable_timeline(tmp_path) -> None:
    db_path = tmp_path / "durable-workflow.db"
    repo = SQLiteRepository(str(db_path))
    timeline = EventTimelineService(repository=repo, persistence_enabled=True)
    registry = build_platform_tool_registry(repo)
    coordinator = WorkflowCoordinator(
        tool_registry=registry,
        profile_memory=ProfileMemoryService(),
        clinical_memory=ClinicalSnapshotMemoryService(),
        event_timeline=timeline,
    )

    live = coordinator.run_alert_workflow(
        user_profile=_user(),
        alert_type="manual_test_alert",
        severity="warning",
        message="hello",
        destinations=["in_app"],
        account_role="admin",
        scopes=["alert:trigger"],
    )

    restarted_repo = SQLiteRepository(str(db_path))
    restarted_timeline = EventTimelineService(repository=restarted_repo, persistence_enabled=True)
    restarted_registry = build_platform_tool_registry(restarted_repo)
    restarted_coordinator = WorkflowCoordinator(
        tool_registry=restarted_registry,
        profile_memory=ProfileMemoryService(),
        clinical_memory=ClinicalSnapshotMemoryService(),
        event_timeline=restarted_timeline,
    )

    replay = restarted_coordinator.replay_workflow(live.correlation_id)

    assert replay.workflow_name == "replay"
    assert replay.replayed is True
    assert [event.event_type for event in replay.timeline_events] == [
        "workflow_started",
        "workflow_completed",
    ]
    assert all(event.correlation_id == live.correlation_id for event in replay.timeline_events)


def test_report_parse_workflow_emits_summary_timeline(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "reports.db"))
    timeline = EventTimelineService()
    coordinator = WorkflowCoordinator(
        tool_registry=build_platform_tool_registry(repo),
        profile_memory=ProfileMemoryService(),
        clinical_memory=ClinicalSnapshotMemoryService(),
        event_timeline=timeline,
    )

    result = coordinator.run_report_parse_workflow(
        user_id="u1",
        request_id="req-report-1",
        correlation_id="corr-report-1",
        source="pasted_text",
        reading_count=4,
        symptom_checkin_count=2,
        red_flag_count=1,
        window={"from": "2026-03-01", "to": "2026-03-07", "limit": 1000},
    )

    assert result.workflow_name == "report_parse"
    events = timeline.list(correlation_id="corr-report-1")
    assert [event.event_type for event in events] == ["workflow_started", "workflow_completed"]
    assert events[0].workflow_name == "report_parse"
    assert events[1].payload["reading_count"] == 4
    assert events[1].payload["symptom_checkin_count"] == 2
    assert events[1].payload["red_flag_count"] == 1
