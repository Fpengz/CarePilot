"""Workflow orchestrator for meal, alert, report, and replay execution."""

from uuid import uuid4

from dietary_guardian.application.meal_analysis import build_meal_analysis_output
from dietary_guardian.domain.alerts.models import AlertSeverity
from dietary_guardian.domain.identity.models import UserProfile
from dietary_guardian.domain.workflows.models import WorkflowExecutionResult, WorkflowName
from dietary_guardian.infrastructure.tooling.registry import ToolRegistry
from dietary_guardian.observability import get_logger
from dietary_guardian.models.contracts import AgentHandoff, CaptureEnvelope
from dietary_guardian.models.meal import VisionResult
from dietary_guardian.models.tooling import ToolPolicyContext
from dietary_guardian.infrastructure.cache import (
    ClinicalSnapshotMemoryService,
    EventTimelineService,
    ProfileMemoryService,
)

logger = get_logger(__name__)

WORKFLOW_DEFINITIONS: dict[WorkflowName, list[str]] = {
    WorkflowName.MEAL_ANALYSIS: ["meal_analysis", "dietary_reasoning", "emit_timeline"],
    WorkflowName.ALERT_ONLY: ["tool_trigger_alert", "emit_timeline"],
    WorkflowName.REPORT_PARSE: ["parse_biomarkers", "summarize_symptoms", "emit_timeline"],
    WorkflowName.REPLAY: ["read_timeline"],
}


class WorkflowCoordinator:
    """Coordinates agent handoffs and durable workflow traces."""

    def __init__(self, *, tool_registry: ToolRegistry, profile_memory: ProfileMemoryService, clinical_memory: ClinicalSnapshotMemoryService, event_timeline: EventTimelineService) -> None:
        self.tool_registry = tool_registry
        self.profile_memory = profile_memory
        self.clinical_memory = clinical_memory
        self.event_timeline = event_timeline

    def run_meal_analysis_workflow(self, *, capture: CaptureEnvelope, vision_result: VisionResult, user_profile: UserProfile, meal_record_id: str | None = None) -> WorkflowExecutionResult:
        self.profile_memory.put(user_profile)
        self.event_timeline.append(
            event_type="workflow_started",
            workflow_name=WorkflowName.MEAL_ANALYSIS,
            correlation_id=capture.correlation_id,
            request_id=capture.request_id,
            user_id=user_profile.id,
            payload={"steps": WORKFLOW_DEFINITIONS[WorkflowName.MEAL_ANALYSIS], "capture_source": capture.source, "meal_filename": capture.filename, "mime_type": capture.mime_type},
        )
        output = build_meal_analysis_output(request_id=capture.request_id, correlation_id=capture.correlation_id, user_id=user_profile.id, profile_mode=user_profile.profile_mode, source=capture.source, vision_result=vision_result)
        handoffs = [AgentHandoff(from_agent="meal_analysis_agent", to_agent="dietary_agent", request_id=capture.request_id, correlation_id=capture.correlation_id, confidence=vision_result.primary_state.confidence_score, obligations=["evaluate_meal_against_clinical_snapshot"], payload={"dish_name": vision_result.primary_state.dish_name})]
        if vision_result.needs_manual_review:
            handoffs.append(AgentHandoff(from_agent="dietary_agent", to_agent="notification_agent", request_id=capture.request_id, correlation_id=capture.correlation_id, confidence=vision_result.primary_state.confidence_score, obligations=["request_clarification_from_patient"], payload={"reason": "manual_review_required"}))
        self.event_timeline.append(
            event_type="workflow_completed",
            workflow_name=WorkflowName.MEAL_ANALYSIS,
            correlation_id=capture.correlation_id,
            request_id=capture.request_id,
            user_id=user_profile.id,
            payload={"dish_name": vision_result.primary_state.dish_name, "manual_review": vision_result.needs_manual_review, "handoff_count": len(handoffs), "meal_record_id": meal_record_id, "confidence": vision_result.primary_state.confidence_score, "estimated_calories": vision_result.primary_state.nutrition.calories, "model_version": vision_result.model_version},
        )
        return WorkflowExecutionResult(workflow_name=WorkflowName.MEAL_ANALYSIS, request_id=capture.request_id, correlation_id=capture.correlation_id, user_id=user_profile.id, output_envelope=output, handoffs=handoffs, timeline_events=self.event_timeline.list(correlation_id=capture.correlation_id))

    def run_alert_workflow(self, *, user_profile: UserProfile, alert_type: str, severity: AlertSeverity, message: str, destinations: list[str], request_id: str | None = None, correlation_id: str | None = None, account_role: str = "member", scopes: list[str] | None = None, environment: str = "dev") -> WorkflowExecutionResult:
        issued_request_id = request_id or str(uuid4())
        issued_correlation_id = correlation_id or str(uuid4())
        self.profile_memory.put(user_profile)
        self.event_timeline.append(event_type="workflow_started", workflow_name=WorkflowName.ALERT_ONLY, correlation_id=issued_correlation_id, request_id=issued_request_id, user_id=user_profile.id, payload={"alert_type": alert_type, "destinations": destinations})
        tool_result = self.tool_registry.execute("trigger_alert", {"alert_type": alert_type, "severity": severity, "message": message, "destinations": destinations}, ToolPolicyContext(account_role=account_role, scopes=scopes or [], environment=environment, user_id=user_profile.id, correlation_id=issued_correlation_id))
        handoffs = [AgentHandoff(from_agent="care_orchestrator", to_agent="notification_agent", request_id=issued_request_id, correlation_id=issued_correlation_id, confidence=1.0 if tool_result.success else 0.0, obligations=["deliver_alert_via_channels"], payload={"alert_type": alert_type, "destinations": destinations})]
        self.event_timeline.append(event_type="workflow_completed", workflow_name=WorkflowName.ALERT_ONLY, correlation_id=issued_correlation_id, request_id=issued_request_id, user_id=user_profile.id, payload={"tool_success": tool_result.success, "tool_name": tool_result.tool_name})
        return WorkflowExecutionResult(workflow_name=WorkflowName.ALERT_ONLY, request_id=issued_request_id, correlation_id=issued_correlation_id, user_id=user_profile.id, handoffs=handoffs, tool_results=[tool_result], timeline_events=self.event_timeline.list(correlation_id=issued_correlation_id))

    def run_report_parse_workflow(self, *, user_id: str, request_id: str, correlation_id: str, source: str, reading_count: int, symptom_checkin_count: int, red_flag_count: int, window: dict[str, object]) -> WorkflowExecutionResult:
        self.event_timeline.append(event_type="workflow_started", workflow_name=WorkflowName.REPORT_PARSE, correlation_id=correlation_id, request_id=request_id, user_id=user_id, payload={"source": source, "steps": WORKFLOW_DEFINITIONS[WorkflowName.REPORT_PARSE]})
        self.event_timeline.append(event_type="workflow_completed", workflow_name=WorkflowName.REPORT_PARSE, correlation_id=correlation_id, request_id=request_id, user_id=user_id, payload={"reading_count": reading_count, "symptom_checkin_count": symptom_checkin_count, "red_flag_count": red_flag_count, "window": window})
        return WorkflowExecutionResult(workflow_name=WorkflowName.REPORT_PARSE, request_id=request_id, correlation_id=correlation_id, user_id=user_id, timeline_events=self.event_timeline.list(correlation_id=correlation_id))

    def replay_workflow(self, correlation_id: str) -> WorkflowExecutionResult:
        events = self.event_timeline.list(correlation_id=correlation_id)
        request_id = events[0].request_id if events else str(uuid4())
        user_id = events[0].user_id if events else None
        logger.info("workflow_replay correlation_id=%s events=%s side_effects=false", correlation_id, len(events))
        return WorkflowExecutionResult(workflow_name=WorkflowName.REPLAY, request_id=request_id or str(uuid4()), correlation_id=correlation_id, user_id=user_id, timeline_events=events, replayed=True)


__all__ = ["WORKFLOW_DEFINITIONS", "WorkflowCoordinator"]
