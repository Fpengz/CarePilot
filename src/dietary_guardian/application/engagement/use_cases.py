"""Application use cases for engagement."""

from __future__ import annotations

from dietary_guardian.domain.care import CaseSnapshot, EngagementAssessment


def assess_engagement(*, snapshot: CaseSnapshot, emotion_signal: str | None) -> EngagementAssessment:
    score = 0
    rationale: list[str] = []

    high_risk_flags = {"high_hba1c", "high_ldl", "high_bp", "symptom_escalation"}
    if high_risk_flags.intersection(snapshot.active_risk_flags):
        score += 2
        rationale.append("clinical risk flags are active")
    if snapshot.meal_risk_streak >= 1:
        score += 1
        rationale.append("recent meal pattern needs intervention")
    if snapshot.reminder_count and snapshot.reminder_response_rate == 0.0:
        score += 1
        rationale.append("medication reminders are going unconfirmed")
    if snapshot.adherence_rate is not None and snapshot.adherence_rate < 0.7:
        score += 1
        rationale.append("adherence rate is below target")
    if snapshot.average_symptom_severity >= 4.0:
        score += 1
        rationale.append("symptom severity is elevated")
    if emotion_signal in {"sad", "frustrated", "anxious"}:
        score += 1
        rationale.append("emotional strain suggests higher disengagement risk")

    if score >= 4:
        risk_level = "high"
    elif score >= 2:
        risk_level = "medium"
    else:
        risk_level = "low"

    if "symptom_escalation" in snapshot.active_risk_flags:
        mode = "escalate"
    elif emotion_signal in {"sad", "frustrated", "anxious"}:
        mode = "supportive"
    elif snapshot.reminder_count and snapshot.reminder_response_rate == 0.0:
        mode = "accountability"
    elif risk_level == "medium":
        mode = "follow_up"
    else:
        mode = "supportive"

    return EngagementAssessment(
        risk_level=risk_level,
        recommended_mode=mode,
        rationale=rationale,
        intervention_opportunities=max(score, 1 if snapshot.active_risk_flags else 0),
    )

