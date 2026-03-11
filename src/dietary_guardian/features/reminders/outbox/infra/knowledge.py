from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class JsonDrugKnowledgeRepository:
    """
    JSON-backed drug knowledge repository.

    Expected directory layout:
        data/drug_knowledge/
            lipid_drugs.json
            hypertension_drugs.json
            diabetes_drugs.json

    Each file can be either:
    1) a list[dict]
    2) {"drugs": list[dict]}
    """

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self._records: list[dict[str, Any]] = []
        self._load_all()

    def _iter_json_files(self) -> list[Path]:
        if not self.data_dir.exists():
            return []
        return sorted(self.data_dir.glob("*.json"))

    def _normalize_records(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if isinstance(payload, dict):
            if isinstance(payload.get("drugs"), list):
                return [item for item in payload["drugs"] if isinstance(item, dict)]
            return [payload]

        return []

    def _load_all(self) -> None:
        self._records.clear()
        for path in self._iter_json_files():
            try:
                with path.open("r", encoding="utf-8") as f:
                    payload = json.load(f)
                self._records.extend(self._normalize_records(payload))
            except Exception:
                # keep startup robust; malformed file is skipped
                continue

    def reload(self) -> None:
        self._load_all()

    def _candidate_names(self, record: dict[str, Any]) -> list[str]:
        names: list[str] = []

        for key in [
            "drug_name_cn",
            "drug_name_en",
            "generic_name",
            "brand_name",
            "name",
        ]:
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                names.append(value.strip())

        aliases = record.get("aliases")
        if isinstance(aliases, list):
            for item in aliases:
                if isinstance(item, str) and item.strip():
                    names.append(item.strip())

        return names

    def _match_score(self, query: str, record: dict[str, Any]) -> int:
        query_norm = query.lower().strip()
        best = 0

        for name in self._candidate_names(record):
            name_norm = name.lower().strip()
            if query_norm == name_norm:
                best = max(best, 100)
            elif query_norm in name_norm or name_norm in query_norm:
                best = max(best, 80)
            elif any(token and token in name_norm for token in query_norm.split()):
                best = max(best, 50)

        return best

    def get_drug_info(self, query: str) -> Optional[dict[str, Any]]:
        query = query.strip()
        if not query:
            return None

        best_record: Optional[dict[str, Any]] = None
        best_score = -1

        for record in self._records:
            score = self._match_score(query, record)
            if score > best_score:
                best_score = score
                best_record = record

        if best_score <= 0:
            return None
        return best_record

    def list_all_drugs(self) -> list[dict[str, Any]]:
        return list(self._records)


class EmptyDrugKnowledgeRepository:
    """
    Null-object fallback repository.
    """

    def get_drug_info(self, query: str) -> Optional[dict[str, Any]]:
        return None