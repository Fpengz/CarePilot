"""
Persist medication records in SQLite.

This module implements SQLite storage for medication regimens and adherence events.
"""

import json
import sqlite3
from datetime import datetime
from typing import Any, cast

from dietary_guardian.features.companion.core.health.models import MedicationAdherenceEvent
from dietary_guardian.features.profiles.domain.models import MealSlot
from dietary_guardian.features.reminders.domain.models import MedicationRegimen
from dietary_guardian.platform.observability.setup import get_logger

logger = get_logger(__name__)


class SQLiteMedicationRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def save_medication_regimen(self, regimen: MedicationRegimen) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO medication_regimens
                (id, user_id, medication_name, dosage_text, timing_type, offset_minutes, slot_scope_json, fixed_time, max_daily_doses, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    regimen.id,
                    regimen.user_id,
                    regimen.medication_name,
                    regimen.dosage_text,
                    regimen.timing_type,
                    regimen.offset_minutes,
                    json.dumps(regimen.slot_scope),
                    regimen.fixed_time,
                    regimen.max_daily_doses,
                    int(regimen.active),
                ),
            )
            conn.commit()
        logger.debug("save_medication_regimen id=%s user_id=%s", regimen.id, regimen.user_id)

    def list_medication_regimens(self, user_id: str, *, active_only: bool = False) -> list[MedicationRegimen]:
        query = (
            "SELECT id, user_id, medication_name, dosage_text, timing_type, offset_minutes, slot_scope_json, "
            "fixed_time, max_daily_doses, active FROM medication_regimens WHERE user_id = ?"
        )
        params: list[Any] = [user_id]
        if active_only:
            query += " AND active = 1"
        query += " ORDER BY medication_name, id"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            MedicationRegimen(
                id=row[0],
                user_id=row[1],
                medication_name=row[2],
                dosage_text=row[3],
                timing_type=row[4],
                offset_minutes=int(row[5]),
                slot_scope=cast(list[MealSlot], json.loads(cast(str, row[6]))),
                fixed_time=row[7],
                max_daily_doses=int(row[8]),
                active=bool(row[9]),
            )
            for row in rows
        ]

    def get_medication_regimen(self, *, user_id: str, regimen_id: str) -> MedicationRegimen | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, user_id, medication_name, dosage_text, timing_type, offset_minutes, slot_scope_json, fixed_time, max_daily_doses, active
                FROM medication_regimens
                WHERE user_id = ? AND id = ?
                """,
                (user_id, regimen_id),
            ).fetchone()
        if row is None:
            return None
        return MedicationRegimen(
            id=row[0],
            user_id=row[1],
            medication_name=row[2],
            dosage_text=row[3],
            timing_type=row[4],
            offset_minutes=int(row[5]),
            slot_scope=cast(list[MealSlot], json.loads(cast(str, row[6]))),
            fixed_time=row[7],
            max_daily_doses=int(row[8]),
            active=bool(row[9]),
        )

    def delete_medication_regimen(self, *, user_id: str, regimen_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM medication_regimens WHERE user_id = ? AND id = ?",
                (user_id, regimen_id),
            )
            conn.commit()
        return cursor.rowcount == 1

    def save_medication_adherence_event(self, event: MedicationAdherenceEvent) -> MedicationAdherenceEvent:
        payload = event.model_dump(mode="json")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO medication_adherence_events
                (id, user_id, regimen_id, reminder_id, status, scheduled_at, taken_at, source, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.user_id,
                    event.regimen_id,
                    event.reminder_id,
                    event.status,
                    event.scheduled_at.isoformat(),
                    event.taken_at.isoformat() if event.taken_at else None,
                    event.source,
                    json.dumps(event.metadata),
                    event.created_at.isoformat(),
                ),
            )
            conn.commit()
        return MedicationAdherenceEvent.model_validate(payload)

    def list_medication_adherence_events(
        self,
        *,
        user_id: str,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[MedicationAdherenceEvent]:
        query = (
            "SELECT id, user_id, regimen_id, reminder_id, status, scheduled_at, taken_at, source, metadata_json, created_at "
            "FROM medication_adherence_events WHERE user_id = ?"
        )
        params: list[Any] = [user_id]
        if start_at is not None:
            query += " AND scheduled_at >= ?"
            params.append(start_at.isoformat())
        if end_at is not None:
            query += " AND scheduled_at <= ?"
            params.append(end_at.isoformat())
        query += " ORDER BY scheduled_at"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            MedicationAdherenceEvent(
                id=row[0],
                user_id=row[1],
                regimen_id=row[2],
                reminder_id=row[3],
                status=row[4],
                scheduled_at=datetime.fromisoformat(row[5]),
                taken_at=datetime.fromisoformat(row[6]) if row[6] else None,
                source=row[7],
                metadata=cast(dict[str, object], json.loads(cast(str, row[8]))),
                created_at=datetime.fromisoformat(row[9]),
            )
            for row in rows
        ]
