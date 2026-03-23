"""
Ingest Singapore food data into the vector store.

This module loads hawker food and drink data into ChromaDB for retrieval.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from care_pilot.platform.persistence.food.local_retriever import (
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    VECTORSTORE_DIR,
)

STATIC_DATA_DIR = Path(__file__).resolve().parents[5] / "src" / "care_pilot" / "data"
HAWKER_JSON = STATIC_DATA_DIR / "food" / "sg_hawker_food.json"
DRINKS_JSON = STATIC_DATA_DIR / "food" / "sg_drinks_and_tips.json"

BATCH_SIZE = 32


class HawkerChunker:
    """Produces nutrition/advice/alternatives chunks for hawker items."""

    @staticmethod
    def chunk(food: dict) -> list[dict]:
        fid = food["food_id"]
        en = food["food_name_en"]
        cn = food.get("food_name_cn", "")
        malay = food.get("food_name_malay", "")
        nut = food.get("nutrition_per_serving", {})
        tags = ", ".join(food.get("health_tags", []))

        base_meta = {
            "food_id": fid,
            "food_name_en": en,
            "food_name_cn": cn,
            "category": food.get("category", ""),
            "cuisine": food.get("cuisine", ""),
            "source": "sg_hawker_local",
        }

        chunks: list[dict] = []

        chunks.append(
            {
                "id": f"{fid}_nutrition",
                "text": (
                    f"{en} ({cn}) | Malay: {malay}\n"
                    f"Category: {food.get('category', '')} | Cuisine: {food.get('cuisine', '')}\n"
                    f"Serving: {food.get('serving_size', '')}\n"
                    f"Calories: {nut.get('calories_kcal', '?')} kcal\n"
                    f"Carbohydrates: {nut.get('carbohydrates_g', '?')}g | Sugar: {nut.get('sugar_g', '?')}g\n"
                    f"Protein: {nut.get('protein_g', '?')}g\n"
                    f"Total fat: {nut.get('total_fat_g', '?')}g | Saturated fat: {nut.get('saturated_fat_g', '?')}g\n"
                    f"Sodium: {nut.get('sodium_mg', '?')}mg | Cholesterol: {nut.get('cholesterol_mg', '?')}mg\n"
                    f"Fibre: {nut.get('fiber_g', '?')}g\n"
                    f"Glycemic index: {food.get('glycemic_index', '')} (GI value: {food.get('gi_value', '?')})\n"
                    f"Health tags: {tags}"
                ),
                "metadata": {**base_meta, "chunk_type": "nutrition"},
            }
        )

        for disease, advice in food.get("disease_advice", {}).items():
            if not advice:
                continue
            risk = advice.get("risk_level", "unknown")
            en_advice = advice.get("en", "")
            cn_advice = advice.get("cn", "")
            chunks.append(
                {
                    "id": f"{fid}_advice_{disease}",
                    "text": (
                        f"{en} ({cn}) — advice for {disease}:\n"
                        f"Risk level: {risk}\n"
                        f"Guidance (EN): {en_advice}\n"
                        f"Guidance (CN): {cn_advice}"
                    ),
                    "metadata": {
                        **base_meta,
                        "chunk_type": f"advice_{disease}",
                        "disease": disease,
                        "risk_level": risk,
                    },
                }
            )

        alts = food.get("healthier_alternatives", [])
        if alts:
            alt_lines = "\n".join(
                f"- {a.get('name_en', '')} ({a.get('name_cn', '')}): {a.get('benefit', '')}"
                for a in alts
            )
            chunks.append(
                {
                    "id": f"{fid}_alternatives",
                    "text": f"Healthier alternatives to {en} ({cn}):\n{alt_lines}",
                    "metadata": {**base_meta, "chunk_type": "alternatives"},
                }
            )

        return chunks


class DrinkChunker:
    """Produces drink info, disease recs, and ordering tips."""

    @staticmethod
    def chunk(data: dict) -> list[dict]:
        chunks: list[dict] = []
        guide = data.get("kopitiam_drink_guide", {})

        for name, info in guide.get("terminology", {}).items():
            text = (
                f"Singapore kopitiam drink: {name}\n"
                f"English: {info.get('en', '')}\n"
                f"Chinese: {info.get('cn', '')}\n"
                f"Calories: {info.get('calories', 'N/A')} kcal | Sugar: {info.get('sugar_g', 'N/A')}g"
            )
            if "note" in info:
                text += f"\nNote: {info['note']}"
            chunks.append(
                {
                    "id": f"drink_{name.replace(' ', '_')}",
                    "text": text,
                    "metadata": {
                        "chunk_type": "drink_info",
                        "drink_name": name,
                        "calories": str(info.get("calories", "")),
                        "sugar_g": str(info.get("sugar_g", "")),
                        "source": "sg_drinks_local",
                    },
                }
            )

        recs = guide.get("diabetes_recommendations", {})
        if recs:
            chunks.append(
                {
                    "id": "drink_recs_diabetes",
                    "text": (
                        "Kopitiam drink recommendations for diabetes patients:\n"
                        f"Best choices (low sugar, safe): {', '.join(recs.get('best_choices', []))}\n"
                        f"Acceptable (in moderation): {', '.join(recs.get('acceptable', []))}\n"
                        f"Limit (occasional only): {', '.join(recs.get('limit', []))}\n"
                        f"Avoid (high sugar, spikes blood glucose): {', '.join(recs.get('avoid', []))}"
                    ),
                    "metadata": {
                        "chunk_type": "drink_recommendations",
                        "disease": "diabetes",
                        "source": "sg_drinks_local",
                    },
                }
            )

        tips = data.get("local_food_ordering_tips", {}).get("useful_phrases", {})
        if tips:
            tip_lines = "\n".join(
                f"- {v.get('en', '')} | CN: {v.get('cn', '')} | Malay: {v.get('malay', 'N/A')}"
                for v in tips.values()
            )
            chunks.append(
                {
                    "id": "ordering_tips",
                    "text": (
                        "Singapore hawker / kopitiam ordering tips for healthier eating:\n"
                        f"{tip_lines}"
                    ),
                    "metadata": {
                        "chunk_type": "ordering_tips",
                        "source": "sg_drinks_local",
                    },
                }
            )

        return chunks


class FoodInfoIngester:
    """Ingest hawker food/drink JSON into ChromaDB collection."""

    def __init__(self) -> None:
        VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(VECTORSTORE_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._model = SentenceTransformer(EMBEDDING_MODEL)

    def _upsert_chunks(self, chunks: list[dict]) -> None:
        ids = [c["id"] for c in chunks]
        docs = [c["text"] for c in chunks]
        metas = [c["metadata"] for c in chunks]

        for i in range(0, len(chunks), BATCH_SIZE):
            batch_ids = ids[i : i + BATCH_SIZE]
            batch_docs = docs[i : i + BATCH_SIZE]
            batch_meta = metas[i : i + BATCH_SIZE]
            embeddings = self._model.encode(batch_docs).tolist()
            self._collection.upsert(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_meta,
                embeddings=embeddings,
            )

    def ingest_hawker(self) -> None:
        if not HAWKER_JSON.exists():
            print(f"[FoodInfoIngester] Missing {HAWKER_JSON}")
            return
        with HAWKER_JSON.open(encoding="utf-8") as handle:
            foods: list[dict[str, Any]] = json.load(handle)
        chunks: list[dict] = []
        for food in foods:
            chunks.extend(HawkerChunker.chunk(food))
        print(f"[FoodInfoIngester] {len(foods)} foods -> {len(chunks)} chunks")
        self._upsert_chunks(chunks)

    def ingest_drinks(self) -> None:
        if not DRINKS_JSON.exists():
            print(f"[FoodInfoIngester] Missing {DRINKS_JSON}")
            return
        with DRINKS_JSON.open(encoding="utf-8") as handle:
            data: dict = json.load(handle)
        chunks = DrinkChunker.chunk(data)
        print(f"[FoodInfoIngester] {len(chunks)} drink chunks")
        self._upsert_chunks(chunks)

    def run(self) -> None:
        self.ingest_hawker()
        self.ingest_drinks()
        total = self._collection.count()
        print(f"[FoodInfoIngester] Done. Collection '{COLLECTION_NAME}' has {total} documents.")


def _smoke_test() -> None:
    from care_pilot.platform.persistence.food.local_retriever import FoodInfoRetriever

    retriever = FoodInfoRetriever(n_results=3)
    queries = [
        "can I drink kopi c if I have diabetes",
        "is nasi lemak safe for hypertension",
        "calories in char kway teow",
        "what can I order instead of teh tarik",
    ]
    for query in queries:
        print(f"\nQuery: {query!r}")
        context = retriever.format_for_context(query)
        print(context or "  (no results)")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _smoke_test()
    else:
        FoodInfoIngester().run()
