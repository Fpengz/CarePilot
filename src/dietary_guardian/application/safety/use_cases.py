from __future__ import annotations

from dietary_guardian.domain.care import (
    CarePlan,
    CaseSnapshot,
    CompanionInteraction,
    EngagementAssessment,
    SafetyDecision,
)


def review_care_plan(
    *,
    interaction: CompanionInteraction,
    snapshot: CaseSnapshot,
    engagement: EngagementAssessment,
    care_plan: CarePlan,
) -> SafetyDecision:
    reasons: list[str] = []
    policy_status = "approved"
    clinician_follow_up = care_plan.clinician_follow_up

    if "symptom_escalation" in snapshot.active_risk_flags or engagement.recommended_mode == "escalate":
        policy_status = "escalate"
        clinician_follow_up = True
        reasons.append("symptom escalation or clinician review threshold is active")
    elif interaction.interaction_type == "report_follow_up" and engagement.risk_level in {"medium", "high"}:
        policy_status = "adjusted"
        clinician_follow_up = True
        reasons.append("biomarker risk requires clinician-visible follow-up guidance")
    elif interaction.interaction_type == "adherence_follow_up" and snapshot.adherence_rate is not None and snapshot.adherence_rate < 0.7:
        policy_status = "adjusted"
        reasons.append("adherence recovery should stay focused on one realistic medication step")

    if not reasons:
        reasons.append("deterministic policy review found no additional restrictions")

    return SafetyDecision(
        policy_status=policy_status,
        clinician_follow_up=clinician_follow_up,
        reasons=reasons,
    )


def apply_safety_decision(*, care_plan: CarePlan, decision: SafetyDecision) -> CarePlan:
    actions = list(care_plan.recommended_actions)
    if decision.policy_status == "escalate":
        actions = actions[:2]
        actions.append("Seek clinician review promptly if symptoms worsen or the concern feels urgent.")
    elif decision.policy_status == "adjusted":
        actions = actions[:2]

    return care_plan.model_copy(
        update={
            "recommended_actions": list(dict.fromkeys(actions)),
            "clinician_follow_up": decision.clinician_follow_up,
            "policy_status": decision.policy_status,
        }
    )
