"""
Generate patient-facing medical cards.

This module composes deterministic companion signals with evidence
snippets and LLM formatting.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, Field

from care_pilot.agent.runtime.inference_types import InferenceModality, InferenceRequest
from care_pilot.config.llm import LLMCapability
from care_pilot.features.companion.core.domain import (
    CaseSnapshot,
    EvidenceBundle,
    EvidenceCitation,
    PersonalizationContext,
)
from care_pilot.features.companion.core.health.blood_pressure import resolve_bp_targets


class InferenceEngineProtocol(Protocol):
    provider: str

    async def infer(self, request: InferenceRequest): ...


class PatientMedicalCard(BaseModel):
    markdown: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    evidence_query: str | None = None
    citations: list[EvidenceCitation] = Field(default_factory=list)


class PatientMedicalCardOutput(BaseModel):
    markdown: str


_SYSTEM_PROMPT = (
    "You are a professional chronic disease management assistant. "
    "Use a calm, encouraging, non-alarming tone. "
    "Return only markdown content. "
    "Do not use emojis."
)

_DISCLAIMER = (
    "※ This card is for informational purposes only and does not replace "
    "professional medical diagnosis. Please consult your doctor promptly."
)


def _build_patient_summary(snapshot: CaseSnapshot) -> str:
    bp = snapshot.blood_pressure_summary
    bp_lines: list[str] = []
    if bp is not None:
        stats = bp.stats
        bp_lines.append(
            f"- Avg BP: {stats.avg_systolic}/{stats.avg_diastolic} mmHg "
            f"(range {stats.min_systolic}-{stats.max_systolic} / "
            f"{stats.min_diastolic}-{stats.max_diastolic})"
        )
        bp_lines.append(
            f"- Trend: {bp.trend.direction} (Δ{bp.trend.delta_systolic:+.1f} systolic)"
        )
        bp_lines.append(
            f"- Abnormal readings: {len(bp.abnormal_readings)}"
        )
    else:
        targets = resolve_bp_targets(snapshot.conditions)
        bp_lines.append(
            f"- Target BP: {targets.systolic}/{targets.diastolic} mmHg (no readings logged)"
        )

    condition_text = ", ".join(snapshot.conditions) if snapshot.conditions else "none"
    medication_text = ", ".join(snapshot.medications) if snapshot.medications else "none"
    return "\n".join(
        [
            f"Patient: {snapshot.profile_name}",
            f"Conditions: {condition_text}",
            f"Medications: {medication_text}",
            *bp_lines,
        ]
    )


def _build_evidence_text(evidence: EvidenceBundle) -> str:
    if not evidence.citations:
        return "No external references available."
    lines = []
    for item in evidence.citations[:6]:
        summary = item.summary.strip()
        if len(summary) > 240:
            summary = summary[:237].rstrip() + "..."
        lines.append(f"- {item.title}: {summary}")
    return "\n".join(lines)


def _ensure_disclaimer(markdown: str) -> str:
    if _DISCLAIMER in markdown:
        return markdown
    return f"{markdown.rstrip()}\n\n{_DISCLAIMER}"


def _fallback_markdown(snapshot: CaseSnapshot, evidence: EvidenceBundle) -> str:
    bp = snapshot.blood_pressure_summary
    if bp is None:
        risk_line = "No blood pressure readings are available yet."
        rec_line = "Please log a home BP reading to personalize guidance."
    else:
        risk_line = (
            f"Average BP is {bp.stats.avg_systolic}/{bp.stats.avg_diastolic} mmHg. "
            f"Trend is {bp.trend.direction}."
        )
        rec_line = (
            "Aim for one low-effort step (e.g., reduce sodium at the next meal) "
            "and recheck BP at the same time of day."
        )

    markdown = "\n".join(
        [
            "## Data Overview",
            _build_patient_summary(snapshot),
            "",
            "## Risk Advisory",
            risk_line,
            "",
            "## Personalized Recommendations",
            rec_line,
            "",
            "## Follow-up Monitoring Advice",
            "Recheck BP 2-3 times per week and log readings consistently.",
            "",
            "## Evidence Highlights",
            _build_evidence_text(evidence),
        ]
    )
    return _ensure_disclaimer(markdown)


async def generate_patient_medical_card(
    *,
    snapshot: CaseSnapshot,
    personalization: PersonalizationContext,
    evidence: EvidenceBundle,
    inference_engine: InferenceEngineProtocol,
) -> PatientMedicalCard:
    prompt = "\n".join(
        [
            "Based on the following patient summary and medical references, "
            "generate a concise patient medical card in Markdown.",
            "",
            "[patient summary]",
            _build_patient_summary(snapshot),
            "",
            "[medical references]",
            _build_evidence_text(evidence),
            "",
            "Output requirements:",
            "1. Sections: ## Data Overview, ## Risk Advisory, "
            "## Personalized Recommendations, ## Follow-up Monitoring Advice",
            "2. Recommendations must be specific and actionable.",
            f"3. Maintain a {personalization.preferred_tone} but professional tone.",
            "4. Do not include citations in the body; keep it easy to read.",
            "5. Do not use emojis.",
            f"6. Include this disclaimer at the end: {_DISCLAIMER}",
        ]
    )
    request = InferenceRequest(
        request_id=f"patient-card-{snapshot.user_id}",
        user_id=snapshot.user_id,
        modality=InferenceModality.TEXT,
        payload={"prompt": prompt},
        safety_context={"contains_healthcare_data": True},
        runtime_profile={"capability": LLMCapability.CLINICAL_SUMMARY.value},
        trace_context={"feature": "patient_medical_card"},
        output_schema=PatientMedicalCardOutput,
        system_prompt=_SYSTEM_PROMPT,
    )

    if getattr(inference_engine, "provider", None) == "test":
        markdown = _fallback_markdown(snapshot, evidence)
    else:
        try:
            response = await inference_engine.infer(request)
            output = response.structured_output
            markdown = _ensure_disclaimer(getattr(output, "markdown", ""))
            if not markdown.strip():
                markdown = _fallback_markdown(snapshot, evidence)
        except Exception:
            markdown = _fallback_markdown(snapshot, evidence)

    return PatientMedicalCard(
        markdown=markdown,
        evidence_query=evidence.query,
        citations=evidence.citations,
    )


__all__ = [
    "PatientMedicalCard",
    "generate_patient_medical_card",
]
