"""
Handle food and nutrition queries for the chat router.

This module enriches diet and meal questions with nutrition context and
Singapore-specific food references.
"""

from __future__ import annotations

import asyncio
import uuid

from care_pilot.features.companion.chat.search_adapter import (
    SearchAgent,
    SearchResult,
)
from care_pilot.features.companion.chat.routes.base import (
    BaseRoute,
    RouteResult,
)
from care_pilot.agent.chat.schemas import ChatSearchQueryOutput, ChatRouteLabel
from care_pilot.agent.runtime.inference_engine import InferenceEngine
from care_pilot.agent.runtime.inference_types import (
    InferenceModality,
    InferenceRequest,
)
from care_pilot.platform.observability import get_logger
from care_pilot.platform.persistence.food.local_retriever import (
    FoodInfoRetriever,
)

_DISTILL_PROMPT = (
    "Convert the user's message into a short, search-engine-friendly phrase (3-6 words) "
    "suitable for finding health and nutrition information. "
    "Include the specific food/drink item, the relevant health angle (e.g. glycemic index, "
    "calories, sodium, saturated fat), and 'Singapore' for local dishes/drinks. "
    "Examples: 'kopi c evaporated milk diabetes Singapore', "
    "'nasi lemak glycemic index diabetes', 'char kway teow sodium hypertension'. "
    "Return the distilled phrase in the `query` field only."
)

SYSTEM_PROMPT = (
    "You are a helpful health assistant for patients in Singapore managing "
    "diabetes, hypertension, or cardiovascular disease. "
    "The user asked about food or diet. "
    "Use the web search results below to give practical advice in the Singapore context. "
    "Include specific values (calories, GI, sodium, saturated fat) where available. "
    "Suggest modifications (e.g. ask for less rice, kopi o kosong instead of teh tarik) "
    "rather than blanket restrictions. "
    "Tailor advice based on their condition if mentioned (diabetes: GI focus; "
    "hypertension: sodium focus; cardiovascular: saturated fat/cholesterol focus)."
)


class FoodRoute(BaseRoute):
    """Enriches food and nutrition queries with live web search results."""

    def __init__(
        self, *, search_agent: SearchAgent, inference_engine: InferenceEngine
    ) -> None:
        self._sa = search_agent
        self._retriever = FoodInfoRetriever(n_results=4)
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
            self._logger.info("chat_food_distill_success term=%s", term)
            return term
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("chat_food_distill_failed error=%s", exc)
            return text

    def enrich(self, text: str) -> RouteResult:
        self._logger.info("chat_food_search_start text=%s", text)
        search_term = self._distill_query(text)
        results: list[SearchResult] = self._sa.search(search_term)

        # ── Local ChromaDB lookup ──────────────────────────────────────
        local_context = self._retriever.format_for_context(text)
        if local_context:
            self._logger.info(
                "chat_food_local_context chars=%s", len(local_context)
            )
        else:
            self._logger.info("chat_food_local_context_empty")

        # ── Web search ────────────────────────────────────────────────
        if not results:
            web_context = None
        else:
            self._logger.info("chat_food_search_results hits=%s", len(results))
            web_lines = ["## Web Search Results"]
            for i, r in enumerate(results, 1):
                web_lines += [
                    f"**[{i}] {r.title}**",
                    f"Source: {r.url}",
                    r.body[:1000].strip(),
                    "",
                ]
            web_context = "\n".join(web_lines)

        if not local_context and not web_context:
            return RouteResult(
                route_name=ChatRouteLabel.FOOD,
                context=None,
                metadata={"hits": 0},
            )

        parts = [SYSTEM_PROMPT, ""]
        if local_context:
            parts.append(local_context)
        if web_context:
            parts.append(web_context)

        return RouteResult(
            route_name=ChatRouteLabel.FOOD,
            context="\n".join(parts),
            metadata={
                "hits": len(results),
                "sources": [r.url for r in results],
            },
        )
