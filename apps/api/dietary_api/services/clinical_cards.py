"""API orchestration for clinician-facing card generation and retrieval.

Shim: business logic lives in
``dietary_guardian.application.clinical_cards.use_cases``.
"""

from __future__ import annotations

from dietary_guardian.application.clinical_cards.use_cases import (  # noqa: F401
    generate_clinical_card_for_session,
    get_clinical_card_for_session,
    list_clinical_cards_for_session,
)

__all__ = [
    "generate_clinical_card_for_session",
    "get_clinical_card_for_session",
    "list_clinical_cards_for_session",
]
