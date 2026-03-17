"""
Retrieve evidence snippets using web search.

This retriever wraps the companion SearchAgent to populate EvidenceBundle
citations for patient and clinician summaries.
"""

from __future__ import annotations

from care_pilot.config.app import get_settings
from care_pilot.config.llm import ModelProvider
from care_pilot.features.companion.chat.search_adapter import SearchAgent, SearchResult
from care_pilot.features.companion.core.domain import (
    CaseSnapshot,
    EvidenceBundle,
    EvidenceCitation,
    InteractionType,
    PersonalizationContext,
)
from care_pilot.features.companion.core.health.blood_pressure import resolve_bp_targets
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


class SearchEvidenceRetriever:
    def __init__(self, *, search_agent: SearchAgent | None = None) -> None:
        self._agent = search_agent or SearchAgent(max_results=3, timeout=8)

    def search_evidence(
        self,
        *,
        interaction_type: InteractionType,
        message: str,
        snapshot: CaseSnapshot,
        personalization: PersonalizationContext,
    ) -> EvidenceBundle:
        if get_settings().llm.provider == ModelProvider.TEST:
            return EvidenceBundle(
                query="test_mode",
                guidance_summary=(
                    f"Anchor guidance in {personalization.recommended_explanation_style} coaching "
                    f"with a {personalization.preferred_tone} tone."
                ),
                citations=[
                    EvidenceCitation(
                        title="Test mode evidence",
                        summary="Evidence retrieval disabled in test mode.",
                        source_type="curated_guidance",
                        relevance="Test-only placeholder.",
                        confidence=0.0,
                        url=None,
                    )
                ],
            )
        queries = _build_queries(snapshot=snapshot, message=message)
        citations: list[EvidenceCitation] = []
        for query in queries:
            results = self._agent.search(query)
            citations.extend(_to_citations(query, results))

        if not citations:
            logger.info("search_evidence_empty fallback=static query_count=%s", len(queries))
            return EvidenceBundle(
                query=", ".join(queries) or "blood pressure support",
                guidance_summary=(
                    f"Anchor guidance in {personalization.recommended_explanation_style} coaching "
                    f"with a {personalization.preferred_tone} tone."
                ),
                citations=[
                    EvidenceCitation(
                        title="General blood pressure guidance",
                        summary=(
                            "Emphasize one low-effort step, reinforce monitoring cadence, "
                            "and encourage clinician follow-up if elevated readings persist."
                        ),
                        source_type="curated_guidance",
                        relevance="Fallback guidance when web search is unavailable.",
                        confidence=0.66,
                        url=None,
                    )
                ],
            )

        return EvidenceBundle(
            query=", ".join(queries) or interaction_type.replace("_", " "),
            guidance_summary=(
                f"Anchor guidance in {personalization.recommended_explanation_style} coaching "
                f"with a {personalization.preferred_tone} tone."
            ),
            citations=citations[:8],
        )


def _build_queries(*, snapshot: CaseSnapshot, message: str) -> list[str]:
    condition = snapshot.conditions[0] if snapshot.conditions else "hypertension"
    targets = resolve_bp_targets(snapshot.conditions)
    queries: list[str] = [f"Blood pressure management targets for {condition}"]
    bp_summary = snapshot.blood_pressure_summary
    if bp_summary is not None:
        avg_sys = bp_summary.stats.avg_systolic
        avg_dia = bp_summary.stats.avg_diastolic
        if avg_sys >= 140 or avg_dia >= 90:
            queries.append(
                f"Antihypertensive treatment regimen for {condition} with high blood pressure"
            )
            queries.append(f"Lifestyle interventions for {condition} with hypertension")
        elif avg_sys >= targets.systolic or avg_dia >= targets.diastolic:
            queries.append(f"Blood pressure management for {condition} with elevated readings")
        else:
            queries.append(
                f"Blood pressure management for {condition} with controlled hypertension"
            )
        if len(bp_summary.abnormal_readings) >= 3:
            queries.append(
                f"Risk assessment for {condition} with significant blood pressure variability"
            )
        if bp_summary.trend.direction == "increase":
            queries.append(f"Causes of rising blood pressure in {condition}")
        elif bp_summary.trend.direction == "decrease":
            queries.append(f"Causes of falling blood pressure in {condition}")
    if "blood pressure" in message.lower() and "monitor" in message.lower():
        queries.append(f"Home blood pressure monitoring guidance for {condition}")
    return list(dict.fromkeys([q for q in queries if q.strip()]))


def _to_citations(_query: str, results: list[SearchResult]) -> list[EvidenceCitation]:
    citations: list[EvidenceCitation] = []
    for result in results[:3]:
        summary = (result.body or "").strip()
        if len(summary) > 240:
            summary = summary[:237].rstrip() + "..."
        citations.append(
            EvidenceCitation(
                title=result.title or "Web evidence",
                summary=summary or "Search result summary unavailable.",
                source_type="web_search",
                relevance="Web search evidence",
                confidence=0.55,
                url=result.url or None,
            )
        )
    return citations


__all__ = ["SearchEvidenceRetriever"]
