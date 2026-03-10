"""Application-layer presenter for meal analysis results."""

from dietary_guardian.models.contracts import (
    AgentExecutionTrace,
    AgentOutputEnvelope,
    AuditRecord,
    DomainDecision,
    EvidenceItem,
    PresentationMessage,
)
from dietary_guardian.models.meal import VisionResult


def build_meal_analysis_output(
    *,
    request_id: str,
    correlation_id: str,
    user_id: str | None,
    profile_mode: str | None,
    source: str,
    vision_result: VisionResult,
) -> AgentOutputEnvelope:
    decision = DomainDecision(
        decision_type="meal_analysis",
        summary=vision_result.primary_state.dish_name,
        confidence=vision_result.primary_state.confidence_score,
        policy_flags=["manual_review"] if vision_result.needs_manual_review else [],
        data=vision_result.model_dump(),
        evidence_items=[
            EvidenceItem(
                source_type="meal_recognition",
                source_id=vision_result.model_version,
                confidence=vision_result.primary_state.confidence_score,
                applicability_scope="meal",
                summary=vision_result.raw_ai_output,
            )
        ],
    )
    presentation = PresentationMessage(
        channel="ui",
        title="Meal Analysis",
        body=f"{vision_result.primary_state.dish_name} (confidence {vision_result.primary_state.confidence_score:.2f})",
        severity="warning" if vision_result.needs_manual_review else "info",
        metadata={"model_version": vision_result.model_version},
    )
    audit = AuditRecord(
        request_id=request_id,
        correlation_id=correlation_id,
        user_id=user_id,
        profile_mode=profile_mode,
        source=source,
        confidence=vision_result.primary_state.confidence_score,
        trace_metadata={"model_version": vision_result.model_version},
    )
    trace = AgentExecutionTrace(
        request_id=request_id,
        correlation_id=correlation_id,
        user_id=user_id,
        profile_mode=profile_mode,
        agent_name="hawker_vision",
        tool_calls=[],
        trace_metadata={"source": source},
    )
    return AgentOutputEnvelope(
        request_id=request_id,
        correlation_id=correlation_id,
        user_id=user_id,
        profile_mode=profile_mode,
        domain_decision=decision,
        presentation_messages=[presentation],
        audit_record=audit,
        trace=trace,
    )
