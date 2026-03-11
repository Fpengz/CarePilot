"""SQLite persistence for clinical data: biomarkers, symptoms, cards, and health profiles."""

import json
import sqlite3
from datetime import datetime
from typing import Any, cast

from dietary_guardian.features.companion.core.health.clinical_card import ClinicalCardRecord
from dietary_guardian.features.companion.core.health.models import (
    BiomarkerReading,
    HealthProfileOnboardingState,
    HealthProfileRecord,
    SymptomCheckIn,
    SymptomSafety,
)
from dietary_guardian.platform.observability.setup import get_logger

logger = get_logger(__name__)


class SQLiteClinicalRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def save_biomarker_readings(self, user_id: str, readings: list[BiomarkerReading]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            for reading in readings:
                conn.execute(
                    """
                    INSERT INTO biomarker_readings
                    (user_id, name, value, unit, reference_range, measured_at, source_doc_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        reading.name,
                        reading.value,
                        reading.unit,
                        reading.reference_range,
                        reading.measured_at.isoformat() if reading.measured_at else None,
                        reading.source_doc_id,
                    ),
                )
            conn.commit()
        logger.info("save_biomarker_readings user_id=%s count=%s", user_id, len(readings))

    def list_biomarker_readings(self, user_id: str) -> list[BiomarkerReading]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT name, value, unit, reference_range, measured_at, source_doc_id
                FROM biomarker_readings WHERE user_id = ?
                ORDER BY measured_at
                """,
                (user_id,),
            ).fetchall()
        readings = [
            BiomarkerReading(
                name=r[0],
                value=r[1],
                unit=r[2],
                reference_range=r[3],
                measured_at=datetime.fromisoformat(r[4]) if r[4] else None,
                source_doc_id=r[5],
            )
            for r in rows
        ]
        logger.debug("list_biomarker_readings user_id=%s count=%s", user_id, len(readings))
        return readings

    def save_symptom_checkin(self, checkin: SymptomCheckIn) -> SymptomCheckIn:
        payload = checkin.model_dump(mode="json")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO symptom_checkins
                (id, user_id, recorded_at, severity, symptom_codes_json, free_text, context_json, safety_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    checkin.id,
                    checkin.user_id,
                    checkin.recorded_at.isoformat(),
                    checkin.severity,
                    json.dumps(checkin.symptom_codes),
                    checkin.free_text,
                    json.dumps(checkin.context),
                    json.dumps(checkin.safety.model_dump(mode="json")),
                ),
            )
            conn.commit()
        return SymptomCheckIn.model_validate(payload)

    def list_symptom_checkins(
        self,
        *,
        user_id: str,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 200,
    ) -> list[SymptomCheckIn]:
        query = (
            "SELECT id, user_id, recorded_at, severity, symptom_codes_json, free_text, context_json, safety_json "
            "FROM symptom_checkins WHERE user_id = ?"
        )
        params: list[Any] = [user_id]
        if start_at is not None:
            query += " AND recorded_at >= ?"
            params.append(start_at.isoformat())
        if end_at is not None:
            query += " AND recorded_at <= ?"
            params.append(end_at.isoformat())
        query += " ORDER BY recorded_at DESC LIMIT ?"
        params.append(max(1, min(limit, 1000)))
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            SymptomCheckIn(
                id=row[0],
                user_id=row[1],
                recorded_at=datetime.fromisoformat(row[2]),
                severity=int(row[3]),
                symptom_codes=cast(list[str], json.loads(cast(str, row[4]))),
                free_text=row[5],
                context=cast(dict[str, object], json.loads(cast(str, row[6]))),
                safety=SymptomSafety.model_validate(json.loads(cast(str, row[7]))),
            )
            for row in rows
        ]

    def save_clinical_card(self, card: ClinicalCardRecord) -> ClinicalCardRecord:
        payload = card.model_dump(mode="json")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO clinical_cards
                (id, user_id, created_at, start_date, end_date, format, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card.id,
                    card.user_id,
                    card.created_at.isoformat(),
                    card.start_date.isoformat(),
                    card.end_date.isoformat(),
                    card.format,
                    json.dumps(payload),
                ),
            )
            conn.commit()
        return ClinicalCardRecord.model_validate(payload)

    def list_clinical_cards(self, *, user_id: str, limit: int = 50) -> list[ClinicalCardRecord]:
        bounded = max(1, min(limit, 200))
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT payload_json FROM clinical_cards
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, bounded),
            ).fetchall()
        return [ClinicalCardRecord.model_validate_json(cast(str, row[0])) for row in rows]

    def get_clinical_card(self, *, user_id: str, card_id: str) -> ClinicalCardRecord | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT payload_json FROM clinical_cards WHERE user_id = ? AND id = ?",
                (user_id, card_id),
            ).fetchone()
        if row is None:
            return None
        return ClinicalCardRecord.model_validate_json(cast(str, row[0]))

    def get_health_profile(self, user_id: str) -> HealthProfileRecord | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM health_profiles
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            logger.debug("get_health_profile_miss user_id=%s", user_id)
            return None
        payload = cast(str, row[0])
        logger.debug("get_health_profile_hit user_id=%s", user_id)
        return HealthProfileRecord.model_validate_json(payload)

    def save_health_profile(self, profile: HealthProfileRecord) -> HealthProfileRecord:
        payload = profile.model_dump(mode="json")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO health_profiles (user_id, updated_at, payload_json)
                VALUES (?, ?, ?)
                """,
                (
                    profile.user_id,
                    str(payload["updated_at"]),
                    json.dumps(payload),
                ),
            )
            conn.commit()
        logger.info("save_health_profile user_id=%s goals=%s", profile.user_id, len(profile.nutrition_goals))
        return profile

    def get_health_profile_onboarding_state(self, user_id: str) -> HealthProfileOnboardingState | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM health_profile_onboarding_states
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            logger.debug("get_health_profile_onboarding_state_miss user_id=%s", user_id)
            return None
        logger.debug("get_health_profile_onboarding_state_hit user_id=%s", user_id)
        return HealthProfileOnboardingState.model_validate_json(cast(str, row[0]))

    def save_health_profile_onboarding_state(
        self,
        state: HealthProfileOnboardingState,
    ) -> HealthProfileOnboardingState:
        payload = state.model_dump(mode="json")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO health_profile_onboarding_states (user_id, updated_at, payload_json)
                VALUES (?, ?, ?)
                """,
                (
                    state.user_id,
                    str(payload["updated_at"]),
                    json.dumps(payload),
                ),
            )
            conn.commit()
        logger.info(
            "save_health_profile_onboarding_state user_id=%s current_step=%s complete=%s",
            state.user_id,
            state.current_step,
            state.is_complete,
        )
        return state
