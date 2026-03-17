"""
Implement evidence retrieval use cases.

This module fetches and prepares evidence snippets used by companion output.
"""

from __future__ import annotations

from care_pilot.features.companion.core.domain import (
    CaseSnapshot,
    EvidenceBundle,
    InteractionType,
    PersonalizationContext,
)

from .ports import EvidenceRetrievalPort


def retrieve_supporting_evidence(
    *,
    retriever: EvidenceRetrievalPort,
    interaction_type: InteractionType,
    message: str,
    snapshot: CaseSnapshot,
    personalization: PersonalizationContext,
) -> EvidenceBundle:
    return retriever.search_evidence(
        interaction_type=interaction_type,
        message=message,
        snapshot=snapshot,
        personalization=personalization,
    )
