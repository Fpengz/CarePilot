"""
Route chat queries to specialized handlers.

This module uses an LLM classifier to map user queries to a route
(drug, food, code, or general) and dispatches to the matching handler.
"""
from __future__ import annotations

from openai import OpenAI

from dietary_guardian.agent.chat.search_adapter import SearchAgent
from dietary_guardian.agent.chat.routes.base import RouteResult
from dietary_guardian.agent.chat.routes.drug_route import DrugRoute
from dietary_guardian.agent.chat.routes.food_route import FoodRoute
from dietary_guardian.agent.chat.routes.code_route import CodeRoute
from dietary_guardian.agent.chat.code_adapter import CodeAgent

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
"""


class QueryRouter:
    """Classifies a query with the LLM and returns an enriched RouteResult."""

    def __init__(
        self,
        *,
        search_agent: SearchAgent,
        client: OpenAI,
        model_id: str,
        code_agent: CodeAgent,
        reasoning_model_id: str,
    ) -> None:
        self._drug_route = DrugRoute(search_agent=search_agent, client=client, model_id=model_id)
        self._food_route = FoodRoute(search_agent=search_agent, client=client, model_id=model_id)
        self._code_route = CodeRoute(agent=code_agent, client=client, model_id=reasoning_model_id)
        self._client = client
        self._model = model_id

    def _classify(self, user_message: str) -> str:
        """
        Ask the LLM to classify the query. Returns 'drug', 'food', or 'general'.
        Falls back to 'general' on any error.
        """
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _CLASSIFICATION_PROMPT},
                    {"role": "user",   "content": user_message},
                ],
                temperature=0,
                max_tokens=5,
            )
            raw_label = resp.choices[0].message.content or ""
            label = raw_label.strip().lower()
            if label not in ("drug", "food", "code", "general"):
                print(f"[Router] Unexpected label {label!r} — falling back to general")
                return "general"
            return label
        except Exception as exc:
            print(f"[Router] Classification error: {exc} — falling back to general")
            return "general"

    def route(self, user_message: str) -> RouteResult:
        """
        Classify the message and dispatch to the right route.
        Returns a RouteResult with context=None for general queries.
        """
        label = self._classify(user_message)
        print(f"[Router] → {label}")

        if label == "drug":
            return self._drug_route.enrich(user_message)
        if label == "food":
            return self._food_route.enrich(user_message)
        if label == "code":
            return self._code_route.enrich(user_message)
        return RouteResult(route_name="general", context=None)
