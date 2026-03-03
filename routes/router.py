"""
routes/router.py
----------------
QueryRouter — uses the LLM to classify the user's query into one of three
routes, then dispatches to the appropriate handler.

The LLM is given plain-language descriptions of each route and returns a
single label. This is more flexible than regex: it handles typos, mixed
languages, implicit meaning, and novel drug/food names without any upkeep.

Routes:
  drug    — Any question about a specific medicine, dosage, side effects,
              interactions, or general medication management for diabetes,
              hypertension, or cardiovascular disease.
  food    — Any question about food, drinks, diet, nutrition, or eating
              habits — including Singapore hawker dishes and kopitiam drinks —
              in relation to health or chronic disease management.
  general — Everything else (no web search; LLM answers from training).
"""
from __future__ import annotations

import os

from openai import OpenAI
from dotenv import load_dotenv

from agents.search_agent import SearchAgent
from routes.base import RouteResult
from routes.drug_route import DrugRoute
from routes.food_route import FoodRoute

load_dotenv()

_CLASSIFICATION_PROMPT = """\
You are a query classifier for a Singapore health assistant app that supports
patients with diabetes, hypertension, and cardiovascular disease.

Classify the user's message into EXACTLY ONE of these three categories:

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

  general — Anything that does not clearly fit drug or food. This includes
              greetings, general health questions, exercise, symptoms,
              emotional support, or unrelated topics.

Respond with ONLY the single word: drug, food, or general.
Do not explain. Do not add punctuation.
"""


class QueryRouter:
    """Classifies a query with the LLM and returns an enriched RouteResult."""

    def __init__(self, search_agent: SearchAgent) -> None:
        self._drug_route = DrugRoute(search_agent)
        self._food_route = FoodRoute(search_agent)
        self._client = OpenAI(
            api_key=os.environ.get("SEALION_API", ""),
            base_url="https://api.sea-lion.ai/v1",
        )
        self._model = os.environ.get(
            "CHAT_MODEL_ID", "aisingapore/Gemma-SEA-LION-v4-27B-IT"
        )

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
            label = resp.choices[0].message.content.strip().lower()
            if label not in ("drug", "food", "general"):
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
        return RouteResult(route_name="general", context=None)
