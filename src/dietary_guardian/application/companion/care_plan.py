"""Application use cases for care plans."""

from __future__ import annotations

from dietary_guardian.domain.companion import (
    CarePlan,
    CaseSnapshot,
    CompanionInteraction,
    EngagementAssessment,
    EvidenceBundle,
    PersonalizationContext,
)


def _message_wants_why(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in ("why", "explain", "understand"))


def _message_wants_one_step(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in ("one", "simple", "realistic", "next step"))


def compose_care_plan(
    *,
    interaction: CompanionInteraction,
    snapshot: CaseSnapshot,
    personalization: PersonalizationContext,
    engagement: EngagementAssessment,
    evidence: EvidenceBundle,
) -> CarePlan:
    wants_why = _message_wants_why(interaction.message)
    wants_one_step = _message_wants_one_step(interaction.message)
    actions: list[str]
    headline: str
    why_now: str
    reasoning_summary: str

    if interaction.interaction_type == "meal_review":
        headline = "Reset the next hawker meal with one realistic swap"
        why_now = "Recent meal and biomarker risk signals suggest the next meal is the fastest point to reduce repeat risk."
        actions = [
            "At the next meal, choose a grilled, soup-based, or less oily option instead of another fried or gravy-heavy dish.",
            "Keep the refined-carb portion smaller and add vegetables or protein so the meal is less likely to spike sugar.",
            "Log the next meal so the companion can compare whether the swap lowered your risk pattern.",
        ]
        reasoning_summary = "Meal review prioritizes repeat meal-risk patterns and a culturally realistic food swap."
    elif interaction.interaction_type == "adherence_follow_up":
        headline = "Protect the next medication dose with one friction-reducing step"
        why_now = "Missed reminders and low adherence are more likely to improve when the recovery step is tiny and immediate."
        actions = [
            "Confirm the very next medication reminder and tie it to the next unavoidable routine, such as leaving home or brushing teeth.",
            "Move the medication or reminder cue to the place where the rush usually happens so the next dose is harder to miss.",
            "If doses keep slipping this week, flag it for clinician review so the regimen barriers can be discussed early.",
        ]
        reasoning_summary = "Adherence follow-up focuses on barrier recovery, not generic health advice."
    elif interaction.interaction_type == "report_follow_up":
        headline = "Turn the latest report into one follow-up priority"
        why_now = "Current biomarker risk flags warrant a concise explanation and a clinician-visible next step."
        actions = [
            "Review the flagged biomarker trend and write down one question to bring to the next clinician conversation.",
            "Use the next meal and symptom check-in to avoid adding more uncertainty while the report concerns are active.",
            "Escalate sooner if symptoms worsen or the reported values continue to trend in the wrong direction.",
        ]
        reasoning_summary = "Report follow-up prioritizes abnormal biomarkers, symptom context, and escalation readiness."
    elif interaction.interaction_type == "chat":
        headline = "Answer the current question and land on one next best action"
        why_now = "The patient explicitly asked for guidance, so the response should clarify the concern and close with an action."
        actions = [
            "Take one practical step today that matches the main concern raised in the message.",
            "Use the next check-in to confirm whether that step reduced the same barrier or symptom.",
        ]
        reasoning_summary = "Chat guidance should honor message intent before defaulting to a generic longitudinal summary."
    else:
        headline = "Stabilize the current risk signals with one manageable step"
        why_now = "The current longitudinal picture shows active opportunities for follow-through and symptom-aware monitoring."
        actions = [
            "Pick the single health action that feels most realistic in the next few hours and complete it before adding another.",
            "Log whether symptoms, meals, or medication follow-through improved after that step.",
            "If the same concern repeats for the rest of the week, surface it in the clinician digest.",
        ]
        reasoning_summary = "Check-ins should translate the current state into one practical next step and one follow-up signal."

    if wants_one_step:
        actions = actions[:1]
    elif wants_why:
        actions = actions[:2]

    urgency = "routine"
    if engagement.risk_level == "high":
        urgency = "prompt"
    elif engagement.risk_level == "medium":
        urgency = "soon"

    summary = (
        f"Focus areas: {', '.join(personalization.focus_areas[:3]) or 'daily routine support'}. "
        f"Use a {personalization.preferred_tone} approach grounded in {personalization.cultural_context.lower()}. "
        f"{evidence.guidance_summary or ''}".strip()
    )
    if wants_why:
        summary = f"{summary} Why this matters: {why_now}"

    return CarePlan(
        interaction_type=interaction.interaction_type,
        headline=headline,
        summary=summary,
        reasoning_summary=reasoning_summary,
        why_now=why_now,
        recommended_actions=actions[:3],
        clinician_follow_up=engagement.risk_level == "high",
        urgency=urgency,
        citations=evidence.citations,
        policy_status="approved",
    )
