"""Application use cases for impact."""

from __future__ import annotations

from dietary_guardian.domain.care import (
    CaseSnapshot,
    CompanionInteraction,
    EngagementAssessment,
    ImpactSummary,
)


def build_impact_summary(
    *,
    snapshot: CaseSnapshot,
    engagement: EngagementAssessment,
    interaction: CompanionInteraction | None = None,
    interventions: list[str] | None = None,
) -> ImpactSummary:
    tracked_metrics: dict[str, float | int] = {
        "meal_count": snapshot.meal_count,
        "meal_risk_streak": snapshot.meal_risk_streak,
        "reminder_count": snapshot.reminder_count,
        "reminder_response_rate": round(snapshot.reminder_response_rate, 4),
        "adherence_events": snapshot.adherence_events,
        "symptom_checkin_count": snapshot.symptom_count,
        "active_risk_flag_count": len(snapshot.active_risk_flags),
    }
    if snapshot.adherence_rate is not None:
        tracked_metrics["adherence_rate"] = round(snapshot.adherence_rate, 4)

    deltas: dict[str, float] = {
        "meal_risk_streak_vs_target": round(0.0 - float(snapshot.meal_risk_streak), 4),
        "reminder_response_rate_vs_target": round(snapshot.reminder_response_rate - 0.6, 4),
        "symptom_severity_vs_target": round(2.0 - float(snapshot.average_symptom_severity), 4),
    }
    if snapshot.adherence_rate is not None:
        deltas["adherence_rate_vs_target"] = round(snapshot.adherence_rate - 0.8, 4)

    improvements: list[str] = []
    if snapshot.adherence_rate is not None and snapshot.adherence_rate >= 0.8:
        improvements.append("Adherence is at or above the target threshold.")
    if snapshot.reminder_count and snapshot.reminder_response_rate >= 0.5:
        improvements.append("Reminder response is showing engagement with follow-through.")
    if not snapshot.active_risk_flags:
        improvements.append("No active risk flags are currently present.")

    interventions_measured = list(interventions or [])
    if not interventions_measured:
        if interaction is not None and interaction.interaction_type == "adherence_follow_up":
            interventions_measured.append("Next-dose recovery plan")
        elif interaction is not None and interaction.interaction_type == "meal_review":
            interventions_measured.append("Next-meal swap plan")
        else:
            interventions_measured.append("Single-step daily support plan")

    return ImpactSummary(
        baseline_window="Current 7-day baseline",
        comparison_window="Next 7-day follow-up",
        tracked_metrics=tracked_metrics,
        deltas=deltas,
        intervention_opportunities=max(engagement.intervention_opportunities, len(snapshot.active_risk_flags)),
        interventions_measured=interventions_measured,
        improvement_signals=improvements,
    )
