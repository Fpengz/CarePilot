"""API orchestration for clinician-facing card generation and retrieval.

Shim: business logic lives in
``care_pilot.features.companion.clinician_digest.clinical_cards.clinical_card_service``.
"""

from __future__ import annotations

from care_pilot.features.companion.clinician_digest.clinical_cards.clinical_card_service import (  # noqa: F401
    generate_clinical_card_for_session,
    get_clinical_card_for_session,
    list_clinical_cards_for_session,
)

__all__ = [
    "generate_clinical_card_for_session",
    "get_clinical_card_for_session",
    "list_clinical_cards_for_session",
]
