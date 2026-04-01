"""
API orchestration for patient-facing medical cards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.api.carepilot_api.deps import AppContext
from care_pilot.config.app import get_settings
from care_pilot.core.contracts.api import PatientMedicalCardResponse
from care_pilot.features.companion.chat.search_adapter import SearchAgent
from care_pilot.features.companion.core.core_service import build_companion_runtime_state
from care_pilot.features.companion.core.domain import CompanionInteraction
from care_pilot.features.companion.core.evidence import retrieve_supporting_evidence
from care_pilot.features.companion.patient_card import generate_patient_medical_card
from care_pilot.platform.persistence.evidence import SearchEvidenceRetriever

from .companion_service import load_companion_inputs

_EVIDENCE_RETRIEVER = SearchEvidenceRetriever(search_agent=SearchAgent(max_results=3, timeout=6))
_CACHE_TTL_SECONDS = get_settings().storage.redis_default_ttl_seconds


def _cache_key(user_id: str) -> str:
    return f"patient_medical_card:{user_id}"


async def generate_patient_medical_card_for_session(
    *,
    context: AppContext,
    session: dict[str, object],
) -> PatientMedicalCardResponse:
    raw_subject = session.get("subject_user_id")
    user_id = (
        str(raw_subject)
        if isinstance(raw_subject, str) and raw_subject
        else str(session.get("user_id"))
    )
    cached = context.cache_store.get_json(_cache_key(user_id))
    if cached is not None:
        return PatientMedicalCardResponse.model_validate(cached)
    inputs = await load_companion_inputs(context=context, session=session)
    interaction = CompanionInteraction(
        interaction_type="check_in",
        message="Generate patient blood pressure medical card.",
        request_id="patient-card",
        correlation_id="patient-card",
        emotion_signal=inputs.emotion_signal,
    )
    runtime = build_companion_runtime_state(interaction=interaction, inputs=inputs)
    evidence = retrieve_supporting_evidence(
        retriever=_EVIDENCE_RETRIEVER,
        interaction_type=interaction.interaction_type,
        message=interaction.message,
        snapshot=runtime.snapshot,
        personalization=runtime.personalization,
    )
    card = await generate_patient_medical_card(
        snapshot=runtime.snapshot,
        personalization=runtime.personalization,
        evidence=evidence,
        inference_engine=context.chat_inference_engine,
    )
    payload = card.model_dump(mode="json")
    context.cache_store.set_json(
        _cache_key(user_id),
        payload,
        ttl_seconds=_CACHE_TTL_SECONDS,
    )
    return PatientMedicalCardResponse.model_validate(payload)
