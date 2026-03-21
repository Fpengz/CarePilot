"""
Persist meal records in SQLite.

This module implements SQLite storage for meal records, observations,
events, and nutrition profiles.
"""

from datetime import datetime

from care_pilot.features.meals.domain import (
    EnrichedMealEvent,
    MealNutritionProfile,
    MealPerception,
)
from care_pilot.features.meals.domain.models import (
    CandidateMealEvent,
    MealCandidateRecord,
    MealState,
    Nutrition,
    NutritionRiskProfile,
    RawObservationBundle,
    ValidatedMealEvent,
)
from care_pilot.features.meals.domain.recognition import MealRecognitionRecord
from care_pilot.platform.observability.setup import get_logger
from care_pilot.platform.persistence.sqlite_db import get_connection

logger = get_logger(__name__)


class SQLiteMealRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def save_meal_record(self, record: MealRecognitionRecord) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO meal_records
                (id, user_id, captured_at, source, meal_state_json, meal_perception_json, enriched_event_json, analysis_version, multi_item_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.user_id,
                    record.captured_at.isoformat(),
                    record.source,
                    record.meal_state.model_dump_json(),
                    (
                        record.meal_perception.model_dump_json()
                        if record.meal_perception is not None
                        else None
                    ),
                    (
                        record.enriched_event.model_dump_json()
                        if record.enriched_event is not None
                        else None
                    ),
                    record.analysis_version,
                    record.multi_item_count,
                ),
            )
            conn.commit()
        logger.info(
            "save_meal_record id=%s user_id=%s dish=%s multi_item_count=%s",
            record.id,
            record.user_id,
            record.meal_state.dish_name,
            record.multi_item_count,
        )

    def list_meal_records(self, user_id: str) -> list[MealRecognitionRecord]:
        legacy_records = self._load_legacy_meal_records(user_id)
        synthesized_records = self._load_v2_meal_records(user_id)
        if legacy_records and synthesized_records:
            merged = [*legacy_records, *synthesized_records]
            merged.sort(key=lambda item: item.captured_at)
            logger.debug(
                "list_meal_records user_id=%s count=%s sources=legacy+v2",
                user_id,
                len(merged),
            )
            return merged
        if legacy_records:
            logger.debug(
                "list_meal_records user_id=%s count=%s source=legacy",
                user_id,
                len(legacy_records),
            )
            return legacy_records
        logger.debug(
            "list_meal_records user_id=%s count=%s source=v2",
            user_id,
            len(synthesized_records),
        )
        return synthesized_records

    def get_meal_record(self, user_id: str, meal_id: str) -> MealRecognitionRecord | None:
        legacy = self._get_legacy_meal_record(user_id, meal_id)
        if legacy is not None:
            return legacy
        event = self.get_validated_meal_event(user_id, meal_id)
        if event is None:
            logger.debug("get_meal_record_miss user_id=%s meal_id=%s", user_id, meal_id)
            return None
        profile = self.get_nutrition_risk_profile(user_id, meal_id)
        return self._build_meal_record_from_event(event, profile)

    def _load_legacy_meal_records(self, user_id: str) -> list[MealRecognitionRecord]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, captured_at, source, meal_state_json, meal_perception_json, enriched_event_json, analysis_version, multi_item_count
                FROM meal_records WHERE user_id = ? ORDER BY captured_at
                """,
                (user_id,),
            ).fetchall()
        out: list[MealRecognitionRecord] = []
        for r in rows:
            out.append(
                MealRecognitionRecord(
                    id=r[0],
                    user_id=r[1],
                    captured_at=datetime.fromisoformat(r[2]),
                    source=r[3],
                    meal_state=MealState.model_validate_json(r[4]),
                    meal_perception=(
                        MealPerception.model_validate_json(r[5]) if r[5] is not None else None
                    ),
                    enriched_event=(
                        EnrichedMealEvent.model_validate_json(r[6]) if r[6] is not None else None
                    ),
                    analysis_version=r[7],
                    multi_item_count=r[8],
                )
            )
        return out

    def _get_legacy_meal_record(self, user_id: str, meal_id: str) -> MealRecognitionRecord | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, user_id, captured_at, source, meal_state_json, meal_perception_json, enriched_event_json, analysis_version, multi_item_count
                FROM meal_records WHERE user_id = ? AND id = ?
                """,
                (user_id, meal_id),
            ).fetchone()
        if row is None:
            return None
        return MealRecognitionRecord(
            id=row[0],
            user_id=row[1],
            captured_at=datetime.fromisoformat(row[2]),
            source=row[3],
            meal_state=MealState.model_validate_json(row[4]),
            meal_perception=(
                MealPerception.model_validate_json(row[5]) if row[5] is not None else None
            ),
            enriched_event=(
                EnrichedMealEvent.model_validate_json(row[6]) if row[6] is not None else None
            ),
            analysis_version=row[7],
            multi_item_count=row[8],
        )

    def _load_v2_meal_records(self, user_id: str) -> list[MealRecognitionRecord]:
        events = self.list_validated_meal_events(user_id)
        if not events:
            return []
        profiles = self.list_nutrition_risk_profiles(user_id)
        profile_map = {profile.event_id: profile for profile in profiles}
        return [
            self._build_meal_record_from_event(event, profile_map.get(event.event_id))
            for event in events
        ]

    def _build_meal_record_from_event(
        self,
        event: ValidatedMealEvent,
        profile: NutritionRiskProfile | None,
    ) -> MealRecognitionRecord:
        confidence = 0.0
        if isinstance(event.confidence_summary, dict):
            raw_value = event.confidence_summary.get("vision_confidence")
            if isinstance(raw_value, (int, float, str)):
                confidence = float(raw_value)
        nutrition = Nutrition(
            calories=profile.calories if profile is not None else 0.0,
            carbs_g=profile.carbs_g if profile is not None else 0.0,
            sugar_g=profile.sugar_g if profile is not None else 0.0,
            protein_g=profile.protein_g if profile is not None else 0.0,
            fat_g=profile.fat_g if profile is not None else 0.0,
            sodium_mg=profile.sodium_mg if profile is not None else 0.0,
            fiber_g=profile.fiber_g if profile is not None else 0.0,
        )
        meal_state = MealState(
            dish_name=event.meal_name,
            confidence_score=confidence,
            identification_method="AI_Flash",
            ingredients=[],
            nutrition=nutrition,
        )
        total_nutrition = MealNutritionProfile.from_legacy(nutrition)
        enriched_event = EnrichedMealEvent(
            meal_name=event.meal_name,
            normalized_items=list(event.canonical_items),
            total_nutrition=total_nutrition,
            risk_tags=list(profile.risk_tags) if profile is not None else [],
            unresolved_items=list(event.alternatives),
            needs_manual_review=event.needs_manual_review,
        )
        source = "reconciled"
        if isinstance(event.provenance, dict):
            source = str(event.provenance.get("source") or source)
        return MealRecognitionRecord(
            id=event.event_id,
            user_id=event.user_id,
            captured_at=event.captured_at,
            source=source,
            meal_state=meal_state,
            meal_perception=None,
            enriched_event=enriched_event,
            analysis_version="v2",
            multi_item_count=max(len(event.canonical_items), 1),
        )

    def save_meal_observation(self, observation: RawObservationBundle) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO meal_observations
                (observation_id, user_id, captured_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    observation.observation_id,
                    observation.user_id,
                    observation.captured_at.isoformat(),
                    observation.model_dump_json(),
                ),
            )
            conn.commit()
        logger.info(
            "save_meal_observation id=%s user_id=%s",
            observation.observation_id,
            observation.user_id,
        )

    def save_meal_candidate(self, record: MealCandidateRecord) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO meal_candidates
                (candidate_id, user_id, created_at, captured_at, confirmation_status, candidate_event_json, observation_id, request_id, correlation_id, source, meal_text, confirmed_at, skipped_at, validated_event_json, nutrition_profile_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.candidate_id,
                    record.user_id,
                    record.created_at.isoformat(),
                    record.captured_at.isoformat(),
                    record.confirmation_status,
                    record.candidate_event.model_dump_json(),
                    record.observation_id,
                    record.request_id,
                    record.correlation_id,
                    record.source,
                    record.meal_text,
                    record.confirmed_at.isoformat() if record.confirmed_at else None,
                    record.skipped_at.isoformat() if record.skipped_at else None,
                    record.validated_event.model_dump_json() if record.validated_event else None,
                    record.nutrition_profile.model_dump_json()
                    if record.nutrition_profile
                    else None,
                ),
            )
            conn.commit()
        logger.info(
            "save_meal_candidate id=%s user_id=%s status=%s",
            record.candidate_id,
            record.user_id,
            record.confirmation_status,
        )

    def get_meal_candidate(self, user_id: str, candidate_id: str) -> MealCandidateRecord | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT candidate_id, user_id, created_at, captured_at, confirmation_status, candidate_event_json, observation_id, request_id, correlation_id, source, meal_text, confirmed_at, skipped_at, validated_event_json, nutrition_profile_json
                FROM meal_candidates WHERE user_id = ? AND candidate_id = ?
                """,
                (user_id, candidate_id),
            ).fetchone()
        if row is None:
            return None
        return MealCandidateRecord(
            candidate_id=row[0],
            user_id=row[1],
            created_at=datetime.fromisoformat(row[2]),
            captured_at=datetime.fromisoformat(row[3]),
            confirmation_status=row[4],
            candidate_event=CandidateMealEvent.model_validate_json(row[5]),
            observation_id=row[6],
            request_id=row[7],
            correlation_id=row[8],
            source=row[9] or "unknown",
            meal_text=row[10],
            confirmed_at=datetime.fromisoformat(row[11]) if row[11] else None,
            skipped_at=datetime.fromisoformat(row[12]) if row[12] else None,
            validated_event=ValidatedMealEvent.model_validate_json(row[13]) if row[13] else None,
            nutrition_profile=NutritionRiskProfile.model_validate_json(row[14])
            if row[14]
            else None,
        )

    def list_meal_observations(self, user_id: str) -> list[RawObservationBundle]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT payload_json FROM meal_observations
                WHERE user_id = ? ORDER BY captured_at
                """,
                (user_id,),
            ).fetchall()
        return [RawObservationBundle.model_validate_json(r[0]) for r in rows]

    def save_validated_meal_event(self, event: ValidatedMealEvent) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO meal_validated_events
                (event_id, user_id, captured_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.user_id,
                    event.captured_at.isoformat(),
                    event.model_dump_json(),
                ),
            )
            conn.commit()
        logger.info(
            "save_validated_meal_event id=%s user_id=%s",
            event.event_id,
            event.user_id,
        )

    def list_validated_meal_events(self, user_id: str) -> list[ValidatedMealEvent]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT payload_json FROM meal_validated_events
                WHERE user_id = ? ORDER BY captured_at
                """,
                (user_id,),
            ).fetchall()
        return [ValidatedMealEvent.model_validate_json(r[0]) for r in rows]

    def get_validated_meal_event(self, user_id: str, event_id: str) -> ValidatedMealEvent | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT payload_json FROM meal_validated_events
                WHERE user_id = ? AND event_id = ?
                """,
                (user_id, event_id),
            ).fetchone()
        if row is None:
            return None
        return ValidatedMealEvent.model_validate_json(row[0])

    def save_nutrition_risk_profile(self, profile: NutritionRiskProfile) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO meal_nutrition_risk_profiles
                (profile_id, event_id, user_id, captured_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    profile.profile_id,
                    profile.event_id,
                    profile.user_id,
                    profile.captured_at.isoformat(),
                    profile.model_dump_json(),
                ),
            )
            conn.commit()
        logger.info(
            "save_nutrition_risk_profile id=%s user_id=%s",
            profile.profile_id,
            profile.user_id,
        )

    def list_nutrition_risk_profiles(self, user_id: str) -> list[NutritionRiskProfile]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT payload_json FROM meal_nutrition_risk_profiles
                WHERE user_id = ? ORDER BY captured_at
                """,
                (user_id,),
            ).fetchall()
        return [NutritionRiskProfile.model_validate_json(r[0]) for r in rows]

    def get_nutrition_risk_profile(
        self, user_id: str, event_id: str
    ) -> NutritionRiskProfile | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT payload_json FROM meal_nutrition_risk_profiles
                WHERE user_id = ? AND event_id = ?
                """,
                (user_id, event_id),
            ).fetchone()
        if row is None:
            return None
        return NutritionRiskProfile.model_validate_json(row[0])
