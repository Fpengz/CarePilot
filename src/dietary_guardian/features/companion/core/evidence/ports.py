"""Application ports for evidence."""

from __future__ import annotations

from typing import Protocol

from dietary_guardian.features.companion.core.domain import (
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
