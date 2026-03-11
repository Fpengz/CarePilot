"""Local Singapore food/drink ChromaDB retriever."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parents[5]
RUNTIME_DATA_DIR = BASE_DIR / "data"
VECTORSTORE_DIR = RUNTIME_DATA_DIR / "vectorstore" / "chroma_db"

COLLECTION_NAME = "sg_food_local"
EMBEDDING_MODEL = "BAAI/bge-m3"


class FoodInfoRetriever:
    """Query interface for the sg_food_local ChromaDB collection."""

    def __init__(self, n_results: int = 4) -> None:
        self._n_results = n_results
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
        """Return top-k matching chunks for query."""
        if self._collection.count() == 0:
            print("[FoodInfoRetriever] Collection is empty; run food ingestion first.")
            return []

        model = self._get_model()
        embedding = model.encode(query).tolist()
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(self._n_results, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict[str, Any]] = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append({"text": doc, "metadata": meta, "distance": dist})

        return hits

    def format_for_context(self, query: str) -> str | None:
        """Format results into a prompt-ready block."""
        hits = self.retrieve(query)
        if not hits:
            return None

        lines = ["## Local Singapore Food Database (exact nutritional data)"]
        for idx, hit in enumerate(hits, 1):
            dist_pct = round((1 - hit["distance"]) * 100, 1)
            label = hit["metadata"].get(
                "food_name_en",
                hit["metadata"].get("drink_name", "Entry"),
            )
            lines.append(f"\n**[Local-{idx}] {label}** (relevance: {dist_pct}%)")
            lines.append(hit["text"])

        return "\n".join(lines)
