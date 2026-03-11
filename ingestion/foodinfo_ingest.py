"""
ingestion/foodinfo_ingest.py
-----------------------------
Ingests Singapore hawker food and kopitiam drink data into ChromaDB
for local cosine-similarity retrieval in FoodRoute.

Two source files:
  data/food/sg_hawker_food.json   — 20 hawker dishes with nutrition & disease advice
  data/food/sg_drinks_and_tips.json — kopitiam drink guide + ordering tips

Collection: sg_food_local (separate from the main food_knowledge collection)
Embeddings: BAAI/bge-m3 via sentence-transformers
Distance:   cosine (ChromaDB default for this collection)

Usage:
    python ingestion/foodinfo_ingest.py          # build / refresh collection
    python ingestion/foodinfo_ingest.py --test   # smoke test retrieval
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR        = Path(__file__).resolve().parent.parent
HAWKER_JSON     = BASE_DIR / "data" / "food" / "sg_hawker_food.json"
DRINKS_JSON     = BASE_DIR / "data" / "food" / "sg_drinks_and_tips.json"
VECTORSTORE_DIR = BASE_DIR / "vectorstore" / "chroma_db"

COLLECTION_NAME  = "sg_food_local"
EMBEDDING_MODEL  = "BAAI/bge-m3"
BATCH_SIZE       = 32


# ===========================================================================
# Chunkers
# ===========================================================================

class HawkerChunker:
    """
    Produces 3 chunk types per hawker food item:
      1. nutrition  — numbers + GI + health tags (answers "what's in X")
      2. advice     — per-disease risk + guidance  (answers "can I eat X with diabetes")
      3. alts       — healthier swap suggestions   (answers "what instead of X")
    """

    @staticmethod
    def chunk(food: dict) -> list[dict]:
        fid   = food["food_id"]
        en    = food["food_name_en"]
        cn    = food.get("food_name_cn", "")
        malay = food.get("food_name_malay", "")
        nut   = food.get("nutrition_per_serving", {})
        tags  = ", ".join(food.get("health_tags", []))

        base_meta = {
            "food_id":      fid,
            "food_name_en": en,
            "food_name_cn": cn,
            "category":     food.get("category", ""),
            "cuisine":      food.get("cuisine", ""),
            "source":       "sg_hawker_local",
        }

        chunks: list[dict] = []

        # ── 1. Nutrition profile ───────────────────────────────────────────
        chunks.append({
            "id":   f"{fid}_nutrition",
            "text": (
                f"{en} ({cn}) | Malay: {malay}\n"
                f"Category: {food.get('category','')} | Cuisine: {food.get('cuisine','')}\n"
                f"Serving: {food.get('serving_size','')}\n"
                f"Calories: {nut.get('calories_kcal','?')} kcal\n"
                f"Carbohydrates: {nut.get('carbohydrates_g','?')}g | Sugar: {nut.get('sugar_g','?')}g\n"
                f"Protein: {nut.get('protein_g','?')}g\n"
                f"Total fat: {nut.get('total_fat_g','?')}g | Saturated fat: {nut.get('saturated_fat_g','?')}g\n"
                f"Sodium: {nut.get('sodium_mg','?')}mg | Cholesterol: {nut.get('cholesterol_mg','?')}mg\n"
                f"Fibre: {nut.get('fiber_g','?')}g\n"
                f"Glycemic index: {food.get('glycemic_index','')} (GI value: {food.get('gi_value','?')})\n"
                f"Health tags: {tags}"
            ),
            "metadata": {**base_meta, "chunk_type": "nutrition"},
        })

        # ── 2. Disease-specific advice (one chunk per disease) ─────────────
        for disease, advice in food.get("disease_advice", {}).items():
            if not advice:
                continue
            risk = advice.get("risk_level", "unknown")
            en_advice = advice.get("en", "")
            cn_advice = advice.get("cn", "")
            chunks.append({
                "id":   f"{fid}_advice_{disease}",
                "text": (
                    f"{en} ({cn}) — advice for {disease}:\n"
                    f"Risk level: {risk}\n"
                    f"Guidance (EN): {en_advice}\n"
                    f"Guidance (CN): {cn_advice}"
                ),
                "metadata": {
                    **base_meta,
                    "chunk_type": f"advice_{disease}",
                    "disease":    disease,
                    "risk_level": risk,
                },
            })

        # ── 3. Healthier alternatives ──────────────────────────────────────
        alts = food.get("healthier_alternatives", [])
        if alts:
            alt_lines = "\n".join(
                f"- {a.get('name_en','')} ({a.get('name_cn','')}): {a.get('benefit','')}"
                for a in alts
            )
            chunks.append({
                "id":   f"{fid}_alternatives",
                "text": (
                    f"Healthier alternatives to {en} ({cn}):\n{alt_lines}"
                ),
                "metadata": {**base_meta, "chunk_type": "alternatives"},
            })

        return chunks


class DrinkChunker:
    """
    Produces chunks from sg_drinks_and_tips.json:
      1. Per drink entry   — name, calories, sugar, description
      2. Disease recs      — best/acceptable/limit/avoid lists per disease
      3. Ordering tips     — local phrases (siu dai, kosong, less rice, etc.)
    """

    @staticmethod
    def chunk(data: dict) -> list[dict]:
        chunks: list[dict] = []
        guide = data.get("kopitiam_drink_guide", {})

        # ── 1. Per drink ───────────────────────────────────────────────────
        for name, info in guide.get("terminology", {}).items():
            text = (
                f"Singapore kopitiam drink: {name}\n"
                f"English: {info.get('en','')}\n"
                f"Chinese: {info.get('cn','')}\n"
                f"Calories: {info.get('calories', 'N/A')} kcal | Sugar: {info.get('sugar_g', 'N/A')}g"
            )
            if "note" in info:
                text += f"\nNote: {info['note']}"
            chunks.append({
                "id":   f"drink_{name.replace(' ', '_')}",
                "text": text,
                "metadata": {
                    "chunk_type": "drink_info",
                    "drink_name": name,
                    "calories":   str(info.get("calories", "")),
                    "sugar_g":    str(info.get("sugar_g", "")),
                    "source":     "sg_drinks_local",
                },
            })

        # ── 2. Diabetes drink recommendations ─────────────────────────────
        recs = guide.get("diabetes_recommendations", {})
        if recs:
            chunks.append({
                "id":   "drink_recs_diabetes",
                "text": (
                    "Kopitiam drink recommendations for diabetes patients:\n"
                    f"Best choices (low sugar, safe): {', '.join(recs.get('best_choices', []))}\n"
                    f"Acceptable (in moderation): {', '.join(recs.get('acceptable', []))}\n"
                    f"Limit (occasional only): {', '.join(recs.get('limit', []))}\n"
                    f"Avoid (high sugar, spikes blood glucose): {', '.join(recs.get('avoid', []))}"
                ),
                "metadata": {
                    "chunk_type": "drink_recommendations",
                    "disease":    "diabetes",
                    "source":     "sg_drinks_local",
                },
            })

        # ── 3. Ordering tips ───────────────────────────────────────────────
        tips = data.get("local_food_ordering_tips", {}).get("useful_phrases", {})
        if tips:
            tip_lines = "\n".join(
                f"- {v.get('en','')} | CN: {v.get('cn','')} | Malay: {v.get('malay','N/A')}"
                for v in tips.values()
            )
            chunks.append({
                "id":   "ordering_tips",
                "text": (
                    "Singapore hawker / kopitiam ordering tips for healthier eating:\n"
                    + tip_lines
                ),
                "metadata": {
                    "chunk_type": "ordering_tips",
                    "source":     "sg_drinks_local",
                },
            })

        return chunks


# ===========================================================================
# Ingester
# ===========================================================================

class FoodInfoIngester:
    """Builds the sg_food_local ChromaDB collection from the two JSON files."""

    def __init__(self) -> None:
        VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(VECTORSTORE_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        print(f"[FoodInfoIngester] Loading embedding model: {EMBEDDING_MODEL}")
        self._model = SentenceTransformer(EMBEDDING_MODEL)

        # Use cosine distance — ChromaDB default is l2; we override per collection
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        print(f"[FoodInfoIngester] Collection '{COLLECTION_NAME}' ready")

    # ------------------------------------------------------------------
    def _embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, batch_size=BATCH_SIZE, show_progress_bar=True).tolist()

    # ------------------------------------------------------------------
    def _upsert_chunks(self, chunks: list[dict]) -> None:
        ids       = [c["id"]   for c in chunks]
        texts     = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        embeddings = self._embed(texts)
        # Upsert in batches
        for i in range(0, len(chunks), BATCH_SIZE):
            self._collection.upsert(
                ids=ids[i : i + BATCH_SIZE],
                documents=texts[i : i + BATCH_SIZE],
                embeddings=embeddings[i : i + BATCH_SIZE],
                metadatas=metadatas[i : i + BATCH_SIZE],
            )
        print(f"[FoodInfoIngester] Upserted {len(chunks)} chunks")

    # ------------------------------------------------------------------
    def ingest_hawker(self) -> None:
        print(f"[FoodInfoIngester] Ingesting {HAWKER_JSON.name} ...")
        with open(HAWKER_JSON, encoding="utf-8") as f:
            foods: list[dict] = json.load(f)
        chunks = []
        for food in foods:
            chunks.extend(HawkerChunker.chunk(food))
        print(f"[FoodInfoIngester]   {len(foods)} foods → {len(chunks)} chunks")
        self._upsert_chunks(chunks)

    def ingest_drinks(self) -> None:
        print(f"[FoodInfoIngester] Ingesting {DRINKS_JSON.name} ...")
        with open(DRINKS_JSON, encoding="utf-8") as f:
            data: dict = json.load(f)
        chunks = DrinkChunker.chunk(data)
        print(f"[FoodInfoIngester]   {len(chunks)} drink chunks")
        self._upsert_chunks(chunks)

    def run(self) -> None:
        self.ingest_hawker()
        self.ingest_drinks()
        total = self._collection.count()
        print(f"[FoodInfoIngester] Done. Collection '{COLLECTION_NAME}' has {total} documents.")


# ===========================================================================
# Retriever  (imported by FoodRoute)
# ===========================================================================

class FoodInfoRetriever:
    """
    Query interface for the sg_food_local ChromaDB collection.
    Returns the top-k most relevant local chunks by cosine similarity.
    Lazy-loads the embedding model on first call.
    """

    def __init__(self, n_results: int = 4) -> None:
        self._n_results  = n_results
        self._model: SentenceTransformer | None = None
        VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(VECTORSTORE_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            print(f"[FoodInfoRetriever] Loading {EMBEDDING_MODEL} ...")
            self._model = SentenceTransformer(EMBEDDING_MODEL)
        return self._model

    def retrieve(self, query: str) -> list[dict[str, Any]]:
        """
        Embed the query and return top-k matching chunks.
        Each result dict has: text, metadata, distance (0=identical, 1=orthogonal).
        """
        if self._collection.count() == 0:
            print("[FoodInfoRetriever] Collection is empty — run foodinfo_ingest.py first")
            return []

        model = self._get_model()
        embedding = model.encode(query).tolist()
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(self._n_results, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append({"text": doc, "metadata": meta, "distance": dist})

        return hits

    def format_for_context(self, query: str) -> str | None:
        """
        Retrieve and format results as a markdown block ready to inject into
        the LLM prompt. Returns None if no results found.
        """
        hits = self.retrieve(query)
        if not hits:
            return None

        lines = ["## Local Singapore Food Database (exact nutritional data)"]
        for i, h in enumerate(hits, 1):
            dist_pct = round((1 - h["distance"]) * 100, 1)
            lines.append(f"\n**[Local-{i}] {h['metadata'].get('food_name_en', h['metadata'].get('drink_name', 'Entry'))}** (relevance: {dist_pct}%)")
            lines.append(h["text"])

        return "\n".join(lines)


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    if "--test" in sys.argv:
        print("\n=== Retrieval smoke test ===")
        retriever = FoodInfoRetriever(n_results=3)
        queries = [
            "can I drink kopi c if I have diabetes",
            "is nasi lemak safe for hypertension",
            "calories in char kway teow",
            "what can I order instead of teh tarik",
        ]
        for q in queries:
            print(f"\nQuery: {q!r}")
            context = retriever.format_for_context(q)
            print(context or "  (no results)")
    else:
        FoodInfoIngester().run()
