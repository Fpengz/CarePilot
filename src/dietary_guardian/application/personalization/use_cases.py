from __future__ import annotations

from dietary_guardian.domain.care import CaseSnapshot, InteractionGoal, InteractionType, PersonalizationContext
from dietary_guardian.models.health_profile import HealthProfileRecord
from dietary_guardian.models.user import UserProfile


def _infer_interaction_goal(*, interaction_type: InteractionType, message: str) -> InteractionGoal:
    lowered = message.lower()
    if interaction_type == "meal_review":
        return "swap" if any(term in lowered for term in ("swap", "replace", "instead")) else "next_step"
    if interaction_type == "adherence_follow_up":
        return "recovery"
    if any(term in lowered for term in ("why", "explain", "understand")):
        return "education"
    if any(term in lowered for term in ("one", "simple", "realistic", "next step")):
        return "next_step"
    return "monitoring"


def build_personalization_context(
    *,
    interaction_type: InteractionType,
    message: str,
    user_profile: UserProfile,
    health_profile: HealthProfileRecord | None,
    snapshot: CaseSnapshot,
    emotion_signal: str | None,
) -> PersonalizationContext:
    focus_areas: list[str] = []
    if snapshot.active_risk_flags:
        focus_areas.extend(snapshot.active_risk_flags)
    if snapshot.meal_risk_streak >= 1:
        focus_areas.append("meal_pattern")
    if snapshot.reminder_count:
        focus_areas.append("adherence")
    if snapshot.symptom_count:
        focus_areas.append("symptom_monitoring")

    barrier_hints: list[str] = []
    if snapshot.reminder_count and snapshot.reminder_response_rate == 0.0:
        barrier_hints.append("reminder follow-through is low")
    if snapshot.meal_risk_streak >= 2:
        barrier_hints.append("repeat risky meal choices")
    if emotion_signal in {"sad", "frustrated", "anxious", "confused"}:
        barrier_hints.append("patient may need a more supportive tone")

    interaction_goal = _infer_interaction_goal(interaction_type=interaction_type, message=message)

    preferred_tone = "practical"
    if emotion_signal in {"sad", "frustrated", "anxious"}:
        preferred_tone = "supportive"
    elif snapshot.reminder_count and snapshot.reminder_response_rate == 0.0:
        preferred_tone = "direct"

    cultural_context = "Singapore hawker routines"
    cuisines = list(user_profile.preferred_cuisines)
    if health_profile is not None and not cuisines:
        cuisines = list(health_profile.preferred_cuisines)
    if cuisines:
        cultural_context = f"Singapore routines with preferred cuisines: {', '.join(cuisines[:3])}"

    explanation_style = "concise"
    if interaction_goal == "education":
        explanation_style = "why-first"
    elif interaction_goal in {"swap", "next_step"}:
        explanation_style = "action-first"

    candidate_modes = [interaction_goal]
    if emotion_signal in {"sad", "frustrated", "anxious"}:
        candidate_modes.append("supportive_coaching")
    if snapshot.reminder_count and snapshot.reminder_response_rate == 0.0:
        candidate_modes.append("friction_reduction")
    if snapshot.meal_risk_streak >= 1:
        candidate_modes.append("meal_swap")

    return PersonalizationContext(
        focus_areas=focus_areas,
        barrier_hints=barrier_hints,
        preferred_tone=preferred_tone,
        cultural_context=cultural_context,
        emotion_signal=emotion_signal,
        interaction_goal=interaction_goal,
        recommended_explanation_style=explanation_style,
        candidate_intervention_modes=list(dict.fromkeys(candidate_modes)),
    )
