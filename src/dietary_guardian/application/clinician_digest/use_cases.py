from __future__ import annotations

from dietary_guardian.domain.care import (
    CarePlan,
    CaseSnapshot,
    ClinicianDigest,
    CompanionInteraction,
    EngagementAssessment,
    EvidenceBundle,
    SafetyDecision,
)


def build_clinician_digest(
    *,
    interaction: CompanionInteraction,
    snapshot: CaseSnapshot,
    engagement: EngagementAssessment,
    care_plan: CarePlan,
    evidence: EvidenceBundle,
    safety: SafetyDecision,
) -> ClinicianDigest:
    changed: list[str] = []
    if snapshot.active_risk_flags:
        changed.append(f"Active risk flags: {', '.join(snapshot.active_risk_flags)}.")
    if snapshot.latest_meal_name:
        changed.append(f"Latest meal logged: {snapshot.latest_meal_name}.")
    if snapshot.reminder_count:
        changed.append(
            f"Reminder response rate: {round(snapshot.reminder_response_rate * 100)}% across {snapshot.reminder_count} reminders."
        )
    if snapshot.symptom_count:
        changed.append(
            f"Symptoms logged: {snapshot.symptom_count} with average severity {snapshot.average_symptom_severity}."
        )

    why_now = care_plan.why_now
    if interaction.interaction_type == "report_follow_up":
        why_now = "Abnormal report-linked biomarkers and current symptoms make this the highest-yield clinician update."
    elif interaction.interaction_type == "adherence_follow_up":
        why_now = "Repeated adherence friction can be addressed earlier if the clinician sees the barrier pattern now."

    priority = "routine"
    if safety.policy_status == "escalate" or engagement.risk_level == "high":
        priority = "urgent"
    elif engagement.risk_level == "medium":
        priority = "watch"

    interventions_attempted: list[str] = []
    if snapshot.reminder_count:
        interventions_attempted.append("Medication reminders were generated for current regimens.")
    if snapshot.meal_count:
        interventions_attempted.append("Meal logging is active and informing current guidance.")
    interventions_attempted.extend(
        f"Companion proposed: {item}" for item in care_plan.recommended_actions[:2]
    )

    summary = (
        f"{snapshot.profile_name} has {engagement.risk_level} near-term engagement risk. "
        f"The companion is prioritizing {', '.join(care_plan.recommended_actions[:2]).lower()}."
    )
    return ClinicianDigest(
        summary=summary,
        what_changed=changed or ["No major longitudinal changes detected."],
        why_now=why_now,
        time_window="Last 7 days",
        priority=priority,
        recommended_actions=care_plan.recommended_actions,
        interventions_attempted=list(dict.fromkeys(interventions_attempted)),
        citations=evidence.citations,
        risk_level=engagement.risk_level,
    )
