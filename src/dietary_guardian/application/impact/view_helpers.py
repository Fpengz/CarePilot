from dietary_guardian.models.analytics import EngagementMetrics
from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.models.recommendation import RecommendationOutput


def build_profile_mode_medication_view(profile_mode: str, reminders: list[ReminderEvent]) -> dict[str, int]:
    if profile_mode == "self":
        return {"due_now": sum(1 for r in reminders if r.status == "sent")}
    if profile_mode == "caregiver":
        return {"missed": sum(1 for r in reminders if r.status == "missed")}
    return {"acknowledged": sum(1 for r in reminders if r.status == "acknowledged")}


def build_profile_mode_report_advice_view(profile_mode: str, recommendation: RecommendationOutput) -> dict[str, str]:
    if profile_mode == "self":
        return {"message": recommendation.localized_advice[0] if recommendation.localized_advice else recommendation.rationale}
    if profile_mode == "caregiver":
        return {"message": recommendation.rationale}
    return {"message": recommendation.rationale, "blocked_reason": recommendation.blocked_reason or ""}


def build_analytics_summary(metrics: EngagementMetrics, reminders: list[ReminderEvent]) -> dict[str, float]:
    acknowledged = sum(1 for event in reminders if event.status == "acknowledged")
    return {
        "mcr": metrics.meal_confirmation_rate,
        "reminders_sent": float(metrics.reminders_sent),
        "acknowledged": float(acknowledged),
    }
