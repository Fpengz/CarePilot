from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

from dietary_guardian.domain.reminders.enums import ReminderState, ReminderType
from dietary_guardian.domain.reminders.models import FoodRecord, MetricReading, Reminder


class SQLiteReminderRepository:
    """
    Unified SQLite repository implementing:
    - ReminderRepository
    - MetricReadingRepository
    - FoodRecordRepository

    This repository is intended to be paired with SQLiteOutboxRepository
    in the same database file.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    reminder_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    state TEXT NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reminders_user_scheduled
                ON reminders(user_id, scheduled_at)
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reminders_state
                ON reminders(state)
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminder_confirmations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reminder_id TEXT NOT NULL,
                    is_taken INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(reminder_id) REFERENCES reminders(id)
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_confirmations_reminder_id
                ON reminder_confirmations(reminder_id)
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metric_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    measured_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    raw_payload_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_metric_readings_user_metric_time
                ON metric_readings(user_id, metric_type, measured_at DESC)
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS food_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    meal_type TEXT NOT NULL,
                    foods_json TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    recorded_at TEXT NOT NULL
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_food_records_user_meal_time
                ON food_records(user_id, meal_type, recorded_at DESC)
                """
            )

    # ------------------------------------------------------------------
    # ReminderRepository
    # ------------------------------------------------------------------

    def save_reminder(self, reminder: Reminder) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO reminders (
                    id, user_id, reminder_type, message, state,
                    scheduled_at, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reminder.reminder_id,
                    reminder.user_id,
                    reminder.reminder_type.value,
                    reminder.message,
                    reminder.state.value,
                    reminder.scheduled_at,
                    reminder.created_at,
                    json.dumps(reminder.payload, ensure_ascii=False),
                ),
            )

    def update_state(self, reminder_id: str, state: ReminderState) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE reminders
                SET state = ?
                WHERE id = ?
                """,
                (state.value, reminder_id),
            )

    def get_reminder(self, reminder_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM reminders
                WHERE id = ?
                """,
                (reminder_id,),
            ).fetchone()

        if row is None:
            return None

        payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "reminder_type": row["reminder_type"],
            "message": row["message"],
            "state": row["state"],
            "scheduled_at": row["scheduled_at"],
            "created_at": row["created_at"],
            "payload": payload,
        }

    def list_reminders(
        self,
        *,
        user_id: Optional[str] = None,
        state: Optional[ReminderState] = None,
        reminder_type: Optional[ReminderType] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []

        if user_id:
            clauses.append("user_id = ?")
            params.append(user_id)
        if state:
            clauses.append("state = ?")
            params.append(state.value)
        if reminder_type:
            clauses.append("reminder_type = ?")
            params.append(reminder_type.value)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM reminders
                {where_sql}
                ORDER BY scheduled_at DESC, created_at DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "reminder_type": row["reminder_type"],
                    "message": row["message"],
                    "state": row["state"],
                    "scheduled_at": row["scheduled_at"],
                    "created_at": row["created_at"],
                    "payload": json.loads(row["payload_json"]) if row["payload_json"] else {},
                }
            )
        return result

    def log_confirmation(self, reminder_id: str, is_taken: bool, timestamp: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO reminder_confirmations (reminder_id, is_taken, timestamp)
                VALUES (?, ?, ?)
                """,
                (reminder_id, int(is_taken), timestamp),
            )

    def get_latest_confirmation(self, reminder_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT reminder_id, is_taken, timestamp
                FROM reminder_confirmations
                WHERE reminder_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (reminder_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "reminder_id": row["reminder_id"],
            "is_taken": bool(row["is_taken"]),
            "timestamp": row["timestamp"],
        }

    # ------------------------------------------------------------------
    # MetricReadingRepository
    # ------------------------------------------------------------------

    def log_metric_reading(self, reading: MetricReading) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO metric_readings (
                    user_id, metric_type, metric_value, unit,
                    measured_at, source, raw_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reading.user_id,
                    reading.metric_type.value,
                    reading.metric_value,
                    reading.unit,
                    reading.measured_at,
                    reading.source,
                    json.dumps(reading.raw_payload, ensure_ascii=False),
                ),
            )

    def get_last_metric_reading(self, user_id: str, metric_type: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM metric_readings
                WHERE user_id = ? AND metric_type = ?
                ORDER BY measured_at DESC, id DESC
                LIMIT 1
                """,
                (user_id, metric_type),
            ).fetchone()

        if row is None:
            return None

        return {
            "user_id": row["user_id"],
            "metric_type": row["metric_type"],
            "metric_value": row["metric_value"],
            "unit": row["unit"],
            "measured_at": row["measured_at"],
            "source": row["source"],
            "raw_payload": json.loads(row["raw_payload_json"]) if row["raw_payload_json"] else {},
        }

    def list_metric_readings(
        self,
        *,
        user_id: str,
        metric_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses = ["user_id = ?"]
        params: list[Any] = [user_id]

        if metric_type:
            clauses.append("metric_type = ?")
            params.append(metric_type)

        where_sql = " AND ".join(clauses)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM metric_readings
                WHERE {where_sql}
                ORDER BY measured_at DESC, id DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "user_id": row["user_id"],
                    "metric_type": row["metric_type"],
                    "metric_value": row["metric_value"],
                    "unit": row["unit"],
                    "measured_at": row["measured_at"],
                    "source": row["source"],
                    "raw_payload": json.loads(row["raw_payload_json"]) if row["raw_payload_json"] else {},
                }
            )
        return result

    # ------------------------------------------------------------------
    # FoodRecordRepository
    # ------------------------------------------------------------------

    def log_food_record(self, record: FoodRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO food_records (
                    user_id, meal_type, foods_json, note, recorded_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record.user_id,
                    record.meal_type,
                    json.dumps(record.foods, ensure_ascii=False),
                    record.note,
                    record.recorded_at,
                ),
            )

    def get_latest_food_record(self, user_id: str, meal_type: Optional[str] = None) -> Optional[dict[str, Any]]:
        if meal_type:
            sql = """
                SELECT *
                FROM food_records
                WHERE user_id = ? AND meal_type = ?
                ORDER BY recorded_at DESC, id DESC
                LIMIT 1
            """
            params = (user_id, meal_type)
        else:
            sql = """
                SELECT *
                FROM food_records
                WHERE user_id = ?
                ORDER BY recorded_at DESC, id DESC
                LIMIT 1
            """
            params = (user_id,)

        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()

        if row is None:
            return None

        return {
            "user_id": row["user_id"],
            "meal_type": row["meal_type"],
            "foods": json.loads(row["foods_json"]) if row["foods_json"] else [],
            "note": row["note"],
            "recorded_at": row["recorded_at"],
        }

    def list_food_records(
        self,
        *,
        user_id: str,
        meal_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses = ["user_id = ?"]
        params: list[Any] = [user_id]

        if meal_type:
            clauses.append("meal_type = ?")
            params.append(meal_type)

        where_sql = " AND ".join(clauses)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM food_records
                WHERE {where_sql}
                ORDER BY recorded_at DESC, id DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "user_id": row["user_id"],
                    "meal_type": row["meal_type"],
                    "foods": json.loads(row["foods_json"]) if row["foods_json"] else [],
                    "note": row["note"],
                    "recorded_at": row["recorded_at"],
                }
            )
        return result