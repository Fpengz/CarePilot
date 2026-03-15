"""
Define evidence retrieval ports.

This module declares the interface used to fetch evidence for companion
responses.
"""

from __future__ import annotations

from typing import Protocol

from care_pilot.features.companion.core.domain import (
    CaseSnapshot,
    EvidenceBundle,
    InteractionType,
    PersonalizationContext,
)


class EvidenceRetrievalPort(Protocol):
    def search_evidence(
        self,
        *,
        interaction_type: InteractionType,
        message: str,
        snapshot: CaseSnapshot,
        personalization: PersonalizationContext,
    ) -> EvidenceBundle: ...
