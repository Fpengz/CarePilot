"""
Run hybrid food search using vector and keyword retrieval.

This module combines vector retrieval with keyword reranking for food search.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

import logfire

BASE_DIR = Path(__file__).resolve().parents[5]
VECTORSTORE_DIR = BASE_DIR / "data" / "vectorstore" / "chroma_db"
EMBEDDING_MODEL = "BAAI/bge-m3"
FOOD_COLLECTION = "sg_food_local"

DISEASE_KEYWORDS = {
    "diabetes": ["diabetes", "糖尿病", "血糖", "hba1c"],
    "hypertension": ["hypertension", "高血压", "血压", "bp"],
    "hyperlipidemia": ["hyperlipidemia", "血脂", "胆固醇", "lipid", "ldl"],
}


class FoodHybridSearch:
    """Food retrieval with vector recall + keyword rerank."""

    def __init__(
        self,
        vector_top_k: int = 20,
        candidate_multiplier: int = 4,
        vectorstore_dir: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self.vector_top_k = vector_top_k
        self.candidate_multiplier = max(2, candidate_multiplier)
        self.vectorstore_dir = vectorstore_dir or str(VECTORSTORE_DIR)
        self.model_name = model_name or EMBEDDING_MODEL

        self.vector_model: SentenceTransformer | None = None
        self.vector_collection = None
        try:
            self.vector_model = SentenceTransformer(self.model_name)
            client = chromadb.PersistentClient(path=self.vectorstore_dir)
            self.vector_collection = client.get_collection(FOOD_COLLECTION)
        except Exception as exc:
            logfire.error(f"[FoodHybridSearch] Vector init failed; keyword-only mode: {exc}")

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search via vector recall + keyword rerank."""
        query = query.strip()
        if not query:
            return []

        disease = self._infer_disease(query)
        candidate_k = max(self.vector_top_k, top_k * self.candidate_multiplier)
        candidates = self._vector_search(query=query, disease=disease, top_k=candidate_k)
        return self._keyword_rerank(query=query, candidates=candidates, top_k=top_k)

    def _vector_search(
        self, *, query: str, disease: str | None, top_k: int
    ) -> list[dict[str, Any]]:
        if not self.vector_model or not self.vector_collection:
            return []

        where = {"disease": disease} if disease else None
        try:
            query_embedding = self.vector_model.encode([query]).tolist()
            kwargs: dict[str, Any] = {
                "query_embeddings": query_embedding,
                "n_results": max(top_k, self.vector_top_k),
            }
            if where:
                kwargs["where"] = where

            rows = self.vector_collection.query(**kwargs)
        except Exception as exc:
            logfire.error(f"[FoodHybridSearch] Vector search failed, fallback to keyword: {exc}")
            return []

        results: list[dict[str, Any]] = []
        documents = rows.get("documents") or [[]]
        metadatas = rows.get("metadatas") or [[]]
        distances = rows.get("distances") or [[]]

        for idx in range(len(documents[0])):
            text = documents[0][idx]
            metadata = metadatas[0][idx] or {}
            distance = float(distances[0][idx]) if distances and distances[0] else 1.0
            results.append(
                {
                    "text": text,
                    "metadata": metadata,
                    "vector_score": round(max(0.0, 1.0 - distance), 4),
                }
            )
        results.sort(key=lambda x: x["vector_score"], reverse=True)
        return results[:top_k]

    def _keyword_rerank(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        if not candidates:
            return []

        query_terms = self._tokenize(query)
        if not query_terms:
            return candidates[:top_k]

        reranked: list[dict[str, Any]] = []
        query_lc = query.lower()
        query_terms_set = set(query_terms)
        for idx, item in enumerate(candidates):
            doc_text = item.get("text", "")
            doc_terms_set = set(self._tokenize(doc_text))
            overlap = len(query_terms_set & doc_terms_set)

            coverage_score = overlap / max(len(query_terms_set), 1)
            phrase_score = 0.15 if query_lc in doc_text.lower() else 0.0

            metadata = item.get("metadata", {}) or {}
            name_boost = 0.0
            for key in ("food_name", "food_name_cn", "drink_name", "food_name_en"):
                val = str(metadata.get(key, "")).lower()
                if val and val in query_lc:
                    name_boost = max(name_boost, 0.2)

            keyword_score = min(1.0, coverage_score + phrase_score + name_boost)

            vector_score = float(item.get("vector_score", 0.0) or 0.0)
            rerank_score = 0.4 * keyword_score + 0.6 * vector_score

            logfire.debug(
                "[FoodHybridSearch] candidate={idx} overlap={overlap} coverage={coverage:.3f} phrase={phrase:.3f} name={name:.3f}",
                idx=idx + 1,
                overlap=overlap,
                coverage=coverage_score,
                phrase=phrase_score,
                name=name_boost,
            )

            row = dict(item)
            row["keyword_score"] = round(keyword_score, 4)
            row["rerank_score"] = round(rerank_score, 4)
            reranked.append(row)

        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]

    def _tokenize(self, text: str) -> list[str]:
        text = text.lower().strip()
        if not text:
            return []

        en_tokens = re.findall(r"[a-z0-9_\-]+", text)
        zh_segments = re.findall(r"[\u4e00-\u9fff]+", text)

        zh_tokens: list[str] = []
        for seg in zh_segments:
            if len(seg) == 1:
                zh_tokens.append(seg)
                continue
            for i in range(len(seg) - 1):
                zh_tokens.append(seg[i : i + 2])
            zh_tokens.append(seg)

        return en_tokens + zh_tokens

    def _infer_disease(self, query: str) -> str | None:
        q = query.lower()
        for disease, words in DISEASE_KEYWORDS.items():
            if any(word in q for word in words):
                return disease
        return None
