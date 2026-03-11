"""
routes/food_route.py
--------------------
Handles food, diet, and nutrition advisory queries for patients managing:
  - Type 2 Diabetes (glycemic index, carb content, blood sugar impact)
  - Hypertension (sodium content, DASH diet, potassium-rich foods)
  - Cardiovascular disease (saturated fat, cholesterol, heart-healthy choices)

Covers Singapore context: hawker dishes, kopitiam drinks, local cuisine.

Activated by: LLM classification in router.py (not regex).
"""
from __future__ import annotations
import os

from openai import OpenAI
from dotenv import load_dotenv

from agents.search_agent import SearchAgent, SearchResult
from ingestion.foodinfo_ingest import FoodInfoRetriever
from routes.base import BaseRoute, RouteResult

load_dotenv()

_DISTILL_PROMPT = (
    "Convert the user's message into a short, search-engine-friendly phrase (3-6 words) "
    "suitable for finding health and nutrition information. "
    "Include the specific food/drink item, the relevant health angle (e.g. glycemic index, "
    "calories, sodium, saturated fat), and 'Singapore' for local dishes/drinks. "
    "Examples: 'kopi c evaporated milk diabetes Singapore', "
    "'nasi lemak glycemic index diabetes', 'char kway teow sodium hypertension'. "
    "Reply with ONLY the search phrase, no explanation."
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

    def __init__(self, search_agent: SearchAgent) -> None:
        self._sa = search_agent
        self._retriever = FoodInfoRetriever(n_results=4)
        self._client = OpenAI(
            api_key=os.environ.get("SEALION_API", ""),
            base_url="https://api.sea-lion.ai/v1",
        )
        self._model = os.environ.get("CHAT_MODEL_ID", "aisingapore/Gemma-SEA-LION-v4-27B-IT")

    def _distill_query(self, text: str) -> str:
        """Use the LLM to extract a focused search term from the user's message."""
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _DISTILL_PROMPT},
                    {"role": "user",   "content": text},
                ],
                temperature=0,
                max_tokens=20,
            )
            term = resp.choices[0].message.content.strip()
            print(f"[FoodRoute] Distilled search term: {term!r}")
            return term
        except Exception as exc:
            print(f"[FoodRoute] Distill error: {exc} — using raw query")
            return text

    def enrich(self, text: str) -> RouteResult:
        print(f"[FoodRoute] Searching: {text!r}")
        search_term = self._distill_query(text)
        results: list[SearchResult] = self._sa.search(search_term)

        # ── Local ChromaDB lookup ──────────────────────────────────────
        local_context = self._retriever.format_for_context(text)
        if local_context:
            print(f"[FoodRoute] Local DB returned context ({len(local_context)} chars):")
            print(local_context)
        else:
            print("[FoodRoute] Local DB: no results")

        # ── Web search ────────────────────────────────────────────────
        if not results:
            web_context = None
        else:
            print(f"[FoodRoute] {len(results)} web result(s):")
            for i, r in enumerate(results, 1):
                print(f"  [{i}] {r.title}")
                print(f"       {r.url}")
                print(f"       {r.body[:600].strip()!r}")
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
            return RouteResult(route_name="food", context=None, metadata={"hits": 0})

        parts = [SYSTEM_PROMPT, ""]
        if local_context:
            parts.append(local_context)
        if web_context:
            parts.append(web_context)

        return RouteResult(
            route_name="food",
            context="\n".join(parts),
            metadata={"hits": len(results), "sources": [r.url for r in results]},
        )
