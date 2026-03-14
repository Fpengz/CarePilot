"""
Handle medication and drug queries for the chat router.

This module enriches medication questions with targeted search results
to improve responses for chronic disease management.
"""
from __future__ import annotations
import asyncio
import uuid

from dietary_guardian.features.companion.chat.search_adapter import SearchAgent, SearchResult
from dietary_guardian.features.companion.chat.routes.base import BaseRoute, RouteResult
from dietary_guardian.agent.chat.schemas import ChatSearchQueryOutput, ChatRouteLabel
from dietary_guardian.agent.runtime.inference_engine import InferenceEngine
from dietary_guardian.agent.runtime.inference_types import InferenceModality, InferenceRequest
from dietary_guardian.platform.observability import get_logger

_DISTILL_PROMPT = (
    "Convert the user's message into a short, search-engine-friendly phrase (3-6 words) "
    "suitable for finding medication information. "
    "Include the specific drug name, the relevant angle (e.g. dosage, side effects, "
    "interactions, CHAS subsidy), and the condition if mentioned. "
    "Examples: 'metformin diabetes side effects Singapore', "
    "'amlodipine hypertension dosage', 'aspirin cardiovascular interactions Singapore'. "
    "Return the distilled phrase in the `query` field only."
)

SYSTEM_PROMPT = (
    "You are a helpful health assistant for patients in Singapore managing "
    "diabetes, hypertension, or cardiovascular disease. "
    "The user asked about a medication. "
    "Use the web search results below to give an accurate, concise answer. "
    "Mention Singapore-specific brand names or subsidies (CHAS/MediSave) where relevant. "
    "Always remind the user to consult their doctor or pharmacist before changing any medication."
)


class DrugRoute(BaseRoute):
    """Enriches drug / medication queries with live web search results."""

    def __init__(self, *, search_agent: SearchAgent, inference_engine: InferenceEngine) -> None:
        self._sa = search_agent
        self._engine = inference_engine
        self._logger = get_logger(__name__)

    def _distill_query(self, text: str) -> str:
        """Use the LLM to extract a focused search term from the user's message."""
        try:
            request = InferenceRequest(
                request_id=str(uuid.uuid4()),
                user_id=None,
                modality=InferenceModality.TEXT,
                payload={"prompt": text},
                output_schema=ChatSearchQueryOutput,
                system_prompt=_DISTILL_PROMPT,
            )
            response = asyncio.run(self._engine.infer(request))
            term = response.structured_output.query.strip()
            self._logger.info("chat_drug_distill_success term=%s", term)
            return term
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("chat_drug_distill_failed error=%s", exc)
            return text

    def enrich(self, text: str) -> RouteResult:
        self._logger.info("chat_drug_search_start text=%s", text)
        search_term = self._distill_query(text)
        results: list[SearchResult] = self._sa.search(search_term)

        if not results:
            return RouteResult(route_name=ChatRouteLabel.DRUG, context=None, metadata={"hits": 0})

        self._logger.info("chat_drug_search_results hits=%s", len(results))

        lines = [SYSTEM_PROMPT, "\n", "## Medication Information (live search results)\n"]
        for i, r in enumerate(results, 1):
            lines += [
                f"**[{i}] {r.title}**",
                f"Source: {r.url}",
                r.body[:1000].strip(),
                "",
            ]

        return RouteResult(
            route_name=ChatRouteLabel.DRUG,
            context="\n".join(lines),
            metadata={"hits": len(results), "sources": [r.url for r in results]},
        )
