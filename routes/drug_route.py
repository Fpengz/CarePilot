"""
routes/drug_route.py
--------------------
Handles queries about medications for patients with:
  • Type 2 Diabetes (e.g. Metformin, SGLT2 inhibitors, GLP-1 agonists)
  • Hypertension (e.g. ACE inhibitors, ARBs, calcium channel blockers)
  • Cardiovascular disease (e.g. statins, antiplatelets, beta-blockers)
  • Any general medication question (dosage, side effects, interactions)

Activated by: LLM classification in router.py (not regex).
Search: DuckDuckGo, Singapore-context biased toward clinical reference sites.
"""
from __future__ import annotations
import os

from openai import OpenAI
from dotenv import load_dotenv

from agents.search_agent import SearchAgent, SearchResult
from routes.base import BaseRoute, RouteResult

load_dotenv()

_DISTILL_PROMPT = (
    "Convert the user's message into a short, search-engine-friendly phrase (3-6 words) "
    "suitable for finding medication information. "
    "Include the specific drug name, the relevant angle (e.g. dosage, side effects, "
    "interactions, CHAS subsidy), and the condition if mentioned. "
    "Examples: 'metformin diabetes side effects Singapore', "
    "'amlodipine hypertension dosage', 'aspirin cardiovascular interactions Singapore'. "
    "Reply with ONLY the search phrase, no explanation."
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

    def __init__(self, search_agent: SearchAgent) -> None:
        self._sa = search_agent
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
            print(f"[DrugRoute] Distilled search term: {term!r}")
            return term
        except Exception as exc:
            print(f"[DrugRoute] Distill error: {exc} — using raw query")
            return text

    def enrich(self, text: str) -> RouteResult:
        print(f"[DrugRoute] Searching: {text!r}")
        search_term = self._distill_query(text)
        results: list[SearchResult] = self._sa.search(search_term)

        if not results:
            return RouteResult(route_name="drug", context=None, metadata={"hits": 0})

        print(f"[DrugRoute] {len(results)} result(s):")
        for i, r in enumerate(results, 1):
            print(f"  [{i}] {r.title}")
            print(f"       {r.url}")
            print(f"       {r.body[:600].strip()!r}")

        lines = [SYSTEM_PROMPT, "\n", "## Medication Information (live search results)\n"]
        for i, r in enumerate(results, 1):
            lines += [
                f"**[{i}] {r.title}**",
                f"Source: {r.url}",
                r.body[:1000].strip(),
                "",
            ]

        return RouteResult(
            route_name="drug",
            context="\n".join(lines),
            metadata={"hits": len(results), "sources": [r.url for r in results]},
        )
