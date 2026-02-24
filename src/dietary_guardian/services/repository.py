import json
import sqlite3
from datetime import datetime
from typing import Any

from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.meal import MealState
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.models.medication import MedicationRegimen, ReminderEvent
from dietary_guardian.models.report import BiomarkerReading

logger = get_logger(__name__)

class SQLiteRepository:
    def __init__(self, db_path: str = "dietary_guardian.db"):
        self.db_path = db_path
        logger.info("repository_init db_path=%s", db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS medication_regimens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    medication_name TEXT NOT NULL,
                    dosage_text TEXT NOT NULL,
                    timing_type TEXT NOT NULL,
                    offset_minutes INTEGER NOT NULL,
                    slot_scope_json TEXT NOT NULL,
                    fixed_time TEXT,
                    max_daily_doses INTEGER NOT NULL,
                    active INTEGER NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS reminder_events (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    medication_name TEXT NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    slot TEXT,
                    dosage_text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    meal_confirmation TEXT NOT NULL,
                    sent_at TEXT,
                    ack_at TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS meal_records (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    meal_state_json TEXT NOT NULL,
                    analysis_version TEXT NOT NULL,
                    multi_item_count INTEGER NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS biomarker_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    reference_range TEXT,
                    measured_at TEXT,
                    source_doc_id TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS recommendation_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user_time ON reminder_events(user_id, scheduled_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_meals_user_time ON meal_records(user_id, captured_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_biomarkers_user_time_name ON biomarker_readings(user_id, measured_at, name)")
            conn.commit()
        logger.info("repository_schema_ready db_path=%s", self.db_path)

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

    def save_reminder_event(self, event: ReminderEvent) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO reminder_events
                (id, user_id, medication_name, scheduled_at, slot, dosage_text, status, meal_confirmation, sent_at, ack_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.user_id,
                    event.medication_name,
                    event.scheduled_at.isoformat(),
                    event.slot,
                    event.dosage_text,
                    event.status,
                    event.meal_confirmation,
                    event.sent_at.isoformat() if event.sent_at else None,
                    event.ack_at.isoformat() if event.ack_at else None,
                ),
            )
            conn.commit()
        logger.debug(
            "save_reminder_event id=%s user_id=%s status=%s",
            event.id,
            event.user_id,
            event.status,
        )

    def get_reminder_event(self, event_id: str) -> ReminderEvent | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, user_id, medication_name, scheduled_at, slot, dosage_text, status, meal_confirmation, sent_at, ack_at
                FROM reminder_events WHERE id = ?
                """,
                (event_id,),
            ).fetchone()
        if row is None:
            logger.debug("get_reminder_event_miss id=%s", event_id)
            return None
        logger.debug("get_reminder_event_hit id=%s", event_id)
        return ReminderEvent(
            id=row[0],
            user_id=row[1],
            medication_name=row[2],
            scheduled_at=datetime.fromisoformat(row[3]),
            slot=row[4],
            dosage_text=row[5],
            status=row[6],
            meal_confirmation=row[7],
            sent_at=datetime.fromisoformat(row[8]) if row[8] else None,
            ack_at=datetime.fromisoformat(row[9]) if row[9] else None,
        )

    def list_reminder_events(self, user_id: str) -> list[ReminderEvent]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, medication_name, scheduled_at, slot, dosage_text, status, meal_confirmation, sent_at, ack_at
                FROM reminder_events WHERE user_id = ? ORDER BY scheduled_at
                """,
                (user_id,),
            ).fetchall()
        events = [
            ReminderEvent(
                id=r[0],
                user_id=r[1],
                medication_name=r[2],
                scheduled_at=datetime.fromisoformat(r[3]),
                slot=r[4],
                dosage_text=r[5],
                status=r[6],
                meal_confirmation=r[7],
                sent_at=datetime.fromisoformat(r[8]) if r[8] else None,
                ack_at=datetime.fromisoformat(r[9]) if r[9] else None,
            )
            for r in rows
        ]
        logger.debug("list_reminder_events user_id=%s count=%s", user_id, len(events))
        return events

    def save_meal_record(self, record: MealRecognitionRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO meal_records
                (id, user_id, captured_at, source, meal_state_json, analysis_version, multi_item_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.user_id,
                    record.captured_at.isoformat(),
                    record.source,
                    record.meal_state.model_dump_json(),
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
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, captured_at, source, meal_state_json, analysis_version, multi_item_count
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
                    analysis_version=r[5],
                    multi_item_count=r[6],
                )
            )
        logger.debug("list_meal_records user_id=%s count=%s", user_id, len(out))
        return out

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

    def save_recommendation(self, user_id: str, payload: dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO recommendation_records(user_id, created_at, payload_json)
                VALUES (?, ?, ?)
                """,
                (user_id, datetime.utcnow().isoformat(), json.dumps(payload)),
            )
            conn.commit()
        logger.info("save_recommendation user_id=%s payload_keys=%s", user_id, sorted(payload.keys()))
