"""Infrastructure support for static retriever."""

from __future__ import annotations

from dietary_guardian.domain.companion import (
    CaseSnapshot,
    EvidenceBundle,
    EvidenceCitation,
    InteractionType,
    PersonalizationContext,
)


class StaticEvidenceRetriever:
    def search_evidence(
        self,
        *,
        interaction_type: InteractionType,
        message: str,
        snapshot: CaseSnapshot,
        personalization: PersonalizationContext,
    ) -> EvidenceBundle:
        lowered = message.lower()
        citations: list[EvidenceCitation] = []
        query_parts = [interaction_type.replace("_", " ")]
        if snapshot.active_risk_flags:
            query_parts.extend(snapshot.active_risk_flags[:2])
        if "meal" in interaction_type or "hawker" in lowered or snapshot.meal_risk_streak >= 1:
            citations.append(
                EvidenceCitation(
                    title="Hawker meal risk reset",
                    summary="Favor a lower-sodium, less oily swap and keep gravy/fried add-ons limited at the next meal.",
                    relevance="Supports one realistic next-meal adjustment in Singapore hawker settings.",
                    confidence=0.81,
                )
            )
        if interaction_type == "adherence_follow_up" or "med" in lowered or "dose" in lowered:
            citations.append(
                EvidenceCitation(
                    title="Medication recovery step",
                    summary="Missed-dose recovery works better when the patient commits to one friction-reducing reminder or placement change.",
                    relevance="Supports a single-step medication adherence recovery plan.",
                    confidence=0.84,
                )
            )
        if interaction_type == "report_follow_up" or any(flag in snapshot.active_risk_flags for flag in ("high_hba1c", "high_ldl", "high_bp")):
            citations.append(
                EvidenceCitation(
                    title="Biomarker follow-up rationale",
                    summary="Abnormal biomarker patterns should be translated into concise follow-up priorities and clinician-visible next steps.",
                    relevance="Supports report and biomarker follow-up planning.",
                    confidence=0.86,
                )
            )
        if not citations:
            citations.append(
                EvidenceCitation(
                    title="Longitudinal coaching default",
                    summary="Use the smallest practical behavior change that matches the patient’s current barriers and readiness.",
                    relevance="Supports general check-in and coaching guidance.",
                    confidence=0.72,
                )
            )

        return EvidenceBundle(
            query=", ".join(dict.fromkeys(query_parts)) or "general chronic care support",
            guidance_summary=(
                f"Anchor the response in {personalization.recommended_explanation_style} coaching with "
                f"{personalization.preferred_tone} tone."
            ),
            citations=citations,
        )
