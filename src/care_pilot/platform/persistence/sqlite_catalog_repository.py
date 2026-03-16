"""
Persist catalog and recommendation data in SQLite.

This module implements SQLite persistence for meal catalogs, canonical foods,
recommendations, and suggestions.
"""

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any, cast

from care_pilot.features.recommendations.domain.canonical_food_matching import (
    find_food_by_name as _find_food_by_name_impl,
)
from care_pilot.features.recommendations.domain.canonical_food_matching import (
    normalize_text,
)
from care_pilot.features.recommendations.domain.models import (
    CanonicalFoodRecord,
    MealCatalogItem,
    PreferenceSnapshot,
    RecommendationInteraction,
)
from care_pilot.platform.observability.setup import get_logger

logger = get_logger(__name__)


class SQLiteCatalogRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def save_recommendation(self, user_id: str, payload: dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO recommendation_records(user_id, created_at, payload_json)
                VALUES (?, ?, ?)
                """,
                (
                    user_id,
                    datetime.now(UTC).isoformat(),
                    json.dumps(payload),
                ),
            )
            conn.commit()
        logger.info(
            "save_recommendation user_id=%s payload_keys=%s",
            user_id,
            sorted(payload.keys()),
        )

    def list_meal_catalog_items(
        self, *, locale: str, slot: str | None = None, limit: int = 100
    ) -> list[MealCatalogItem]:
        bounded = max(1, min(int(limit), 200))
        query = """
            SELECT payload_json FROM meal_catalog
            WHERE locale = ? AND active = 1
        """
        params: list[object] = [locale]
        if slot is not None:
            query += " AND slot = ?"
            params.append(slot)
        query += " ORDER BY meal_id LIMIT ?"
        params.append(bounded)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [MealCatalogItem.model_validate_json(cast(str, row[0])) for row in rows]

    def get_meal_catalog_item(self, meal_id: str) -> MealCatalogItem | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT payload_json FROM meal_catalog WHERE meal_id = ?",
                (meal_id,),
            ).fetchone()
        if row is None:
            return None
        return MealCatalogItem.model_validate_json(cast(str, row[0]))

    def list_canonical_foods(
        self,
        *,
        locale: str,
        slot: str | None = None,
        limit: int = 100,
    ) -> list[CanonicalFoodRecord]:
        bounded = max(1, min(int(limit), 500))
        query = """
            SELECT payload_json FROM canonical_foods
            WHERE locale = ? AND active = 1
        """
        params: list[object] = [locale]
        if slot is not None:
            query += " AND slot = ?"
            params.append(slot)
        query += " ORDER BY food_id LIMIT ?"
        params.append(bounded)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [CanonicalFoodRecord.model_validate_json(cast(str, row[0])) for row in rows]

    def get_canonical_food(self, food_id: str) -> CanonicalFoodRecord | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT payload_json FROM canonical_foods WHERE food_id = ?",
                (food_id,),
            ).fetchone()
        if row is None:
            return None
        return CanonicalFoodRecord.model_validate_json(cast(str, row[0]))

    def find_food_by_name(self, *, locale: str, name: str) -> CanonicalFoodRecord | None:
        normalized = normalize_text(name)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT cf.payload_json
                FROM food_alias fa
                JOIN canonical_foods cf ON cf.food_id = fa.food_id
                WHERE fa.alias = ? AND cf.locale = ? AND cf.active = 1
                ORDER BY fa.priority ASC
                LIMIT 1
                """,
                (normalized, locale),
            ).fetchone()
        if row is not None:
            return CanonicalFoodRecord.model_validate_json(cast(str, row[0]))
        return _find_food_by_name_impl(
            self.list_canonical_foods(locale=locale, limit=500),
            name,
            locale=locale,
        )

    def save_recommendation_interaction(
        self, interaction: RecommendationInteraction
    ) -> RecommendationInteraction:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO recommendation_interactions
                (interaction_id, user_id, recommendation_id, candidate_id, event_type, slot, source_meal_id, selected_meal_id, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    interaction.interaction_id,
                    interaction.user_id,
                    interaction.recommendation_id,
                    interaction.candidate_id,
                    interaction.event_type,
                    interaction.slot,
                    interaction.source_meal_id,
                    interaction.selected_meal_id,
                    interaction.created_at.isoformat(),
                    json.dumps(interaction.metadata),
                ),
            )
            conn.commit()
        logger.info(
            "save_recommendation_interaction user_id=%s candidate_id=%s event_type=%s",
            interaction.user_id,
            interaction.candidate_id,
            interaction.event_type,
        )
        return interaction

    def list_recommendation_interactions(
        self, user_id: str, *, limit: int = 200
    ) -> list[RecommendationInteraction]:
        bounded = max(1, min(int(limit), 1000))
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT interaction_id, user_id, recommendation_id, candidate_id, event_type, slot, source_meal_id, selected_meal_id, created_at, metadata_json
                FROM recommendation_interactions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, bounded),
            ).fetchall()
        return [
            RecommendationInteraction(
                interaction_id=row[0],
                user_id=row[1],
                recommendation_id=row[2],
                candidate_id=row[3],
                event_type=row[4],
                slot=row[5],
                source_meal_id=row[6],
                selected_meal_id=row[7],
                created_at=datetime.fromisoformat(row[8]),
                metadata=cast(dict[str, object], json.loads(cast(str, row[9]))),
            )
            for row in rows
        ]

    def get_preference_snapshot(self, user_id: str) -> PreferenceSnapshot | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT payload_json FROM preference_snapshots WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            logger.debug("get_preference_snapshot_miss user_id=%s", user_id)
            return None
        return PreferenceSnapshot.model_validate_json(cast(str, row[0]))

    def save_preference_snapshot(self, snapshot: PreferenceSnapshot) -> PreferenceSnapshot:
        payload = snapshot.model_dump(mode="json")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO preference_snapshots (user_id, updated_at, payload_json)
                VALUES (?, ?, ?)
                """,
                (
                    snapshot.user_id,
                    snapshot.updated_at.isoformat(),
                    json.dumps(payload),
                ),
            )
            conn.commit()
        logger.info(
            "save_preference_snapshot user_id=%s interactions=%s",
            snapshot.user_id,
            snapshot.interaction_count,
        )
        return snapshot

    def save_suggestion_record(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        suggestion_id = str(payload.get("suggestion_id", ""))
        created_at = str(payload.get("created_at", ""))
        if not suggestion_id or not created_at:
            raise ValueError("suggestion payload requires suggestion_id and created_at")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO suggestion_records(suggestion_id, user_id, created_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (suggestion_id, user_id, created_at, json.dumps(payload)),
            )
            conn.commit()
        logger.info(
            "save_suggestion_record user_id=%s suggestion_id=%s",
            user_id,
            suggestion_id,
        )
        return payload

    def list_suggestion_records(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(limit, 100))
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM suggestion_records
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, bounded_limit),
            ).fetchall()
        items = [json.loads(cast(str, row[0])) for row in rows]
        logger.debug("list_suggestion_records user_id=%s count=%s", user_id, len(items))
        return items

    def get_suggestion_record(self, user_id: str, suggestion_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM suggestion_records
                WHERE user_id = ? AND suggestion_id = ?
                """,
                (user_id, suggestion_id),
            ).fetchone()
        if row is None:
            logger.debug(
                "get_suggestion_record_miss user_id=%s suggestion_id=%s",
                user_id,
                suggestion_id,
            )
            return None
        item = json.loads(cast(str, row[0]))
        logger.debug(
            "get_suggestion_record_hit user_id=%s suggestion_id=%s",
            user_id,
            suggestion_id,
        )
        return item
