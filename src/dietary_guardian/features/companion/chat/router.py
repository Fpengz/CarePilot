"""
Route chat queries to specialized handlers.

This module uses an LLM classifier to map user queries to a route
(drug, food, code, or general) and dispatches to the matching handler.
"""
from __future__ import annotations

import asyncio
import uuid

from dietary_guardian.features.companion.chat.search_adapter import SearchAgent
from dietary_guardian.features.companion.chat.routes.base import RouteResult
from dietary_guardian.features.companion.chat.routes.drug_route import DrugRoute
from dietary_guardian.features.companion.chat.routes.food_route import FoodRoute
from dietary_guardian.features.companion.chat.routes.code_route import CodeRoute
from dietary_guardian.features.companion.chat.code_adapter import CodeAgent
from dietary_guardian.agent.chat.schemas import ChatClassificationOutput, ChatRouteLabel
from dietary_guardian.agent.runtime.inference_engine import InferenceEngine
from dietary_guardian.agent.runtime.inference_types import InferenceModality, InferenceRequest
from dietary_guardian.platform.observability import get_logger

_CLASSIFICATION_PROMPT = """\
You are a query classifier for a Singapore health assistant app that supports
patients with diabetes, hypertension, and cardiovascular disease.

Classify the user's message into EXACTLY ONE of these four categories:

  drug    — The query is about a specific medicine, drug, tablet, capsule,
              dosage instructions, side effects, drug interactions, missed
              doses, or any other medication-related question. This includes
              brand names, generic names, or phrases like "my doctor prescribed
              me X" or "ubat kencing manis" or "我的速鳟".

  food    — The query is about food, drinks, diet, eating habits, nutrition,
              or whether something is safe/healthy to consume. This includes
              Singapore hawker food (chicken rice, laksa, char kway teow),
              kopitiam drinks (kopi, teh, milo, bandung, kosong, siu dai),
              calorie/GI/sodium questions, or asking "can I eat X" given a
              health condition.

  code    — The user explicitly wants a number calculated, computed, or
              derived from a formula. Examples: "how many calories in 3 plates
              of chicken rice?", "calculate my BMI", "what is 250mg x 3 doses?",
              "convert 180 lbs to kg", or any arithmetic/unit-conversion request.

  general — Anything that does not clearly fit drug, food, or code. This
              includes greetings, general health questions, exercise, symptoms,
              emotional support, or unrelated topics.

Respond with ONLY the single word: drug, food, code, or general.
Do not explain. Do not add punctuation.
Return the label in the `label` field only.
"""


class QueryRouter:
    """Classifies a query with the LLM and returns an enriched RouteResult."""

    def __init__(
        self,
        *,
        search_agent: SearchAgent,
        inference_engine: InferenceEngine,
        code_agent: CodeAgent,
        reasoning_engine: InferenceEngine,
    ) -> None:
        self._drug_route = DrugRoute(search_agent=search_agent, inference_engine=inference_engine)
        self._food_route = FoodRoute(search_agent=search_agent, inference_engine=inference_engine)
        self._code_route = CodeRoute(agent=code_agent, inference_engine=reasoning_engine)
        self._engine = inference_engine
        self._logger = get_logger(__name__)

    def _classify(self, user_message: str) -> ChatRouteLabel:
        """
        Ask the LLM to classify the query. Returns 'drug', 'food', or 'general'.
        Falls back to 'general' on any error.
        """
        try:
            request = InferenceRequest(
                request_id=str(uuid.uuid4()),
                user_id=None,
                modality=InferenceModality.TEXT,
                payload={"prompt": user_message},
                output_schema=ChatClassificationOutput,
                system_prompt=_CLASSIFICATION_PROMPT,
            )
            response = asyncio.run(self._engine.infer(request))
            return response.structured_output.label
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("chat_router_classification_failed error=%s", exc)
            return ChatRouteLabel.GENERAL

    def route(self, user_message: str) -> RouteResult:
        """
        Classify the message and dispatch to the right route.
        Returns a RouteResult with context=None for general queries.
        """
        label = self._classify(user_message)
        self._logger.info("chat_router_route label=%s", label)

        if label == ChatRouteLabel.DRUG:
            return self._drug_route.enrich(user_message)
        if label == ChatRouteLabel.FOOD:
            return self._food_route.enrich(user_message)
        if label == ChatRouteLabel.CODE:
            return self._code_route.enrich(user_message)
        return RouteResult(route_name=ChatRouteLabel.GENERAL, context=None)
