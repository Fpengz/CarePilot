"""
Build companion context used by API services.

This module assembles clinical snapshots, evidence, and session context
required to drive companion orchestration responses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from care_pilot.features.companion.core.evidence.ports import EvidenceRetrievalPort
from care_pilot.platform.observability import get_logger
from care_pilot.platform.persistence.evidence import SearchEvidenceRetriever

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

_EVIDENCE_RETRIEVER: EvidenceRetrievalPort = SearchEvidenceRetriever(
    # Evidence is retrieved via standard search engine protocols
)
