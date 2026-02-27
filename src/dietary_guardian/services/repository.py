import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.meal import MealState
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.models.medication import MedicationRegimen, ReminderEvent
from dietary_guardian.models.report import BiomarkerReading
from dietary_guardian.models.alerting import AlertMessage, OutboxRecord

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
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS suggestion_records (
                    suggestion_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_outbox (
                    alert_id TEXT NOT NULL,
                    sink TEXT NOT NULL,
                    type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    next_attempt_at TEXT NOT NULL,
                    last_error TEXT,
                    lease_owner TEXT,
                    lease_until TEXT,
                    idempotency_key TEXT NOT NULL,
                    PRIMARY KEY (alert_id, sink)
                )
                """
            )
            # Backward-compatible migration for databases created before payload fields existed.
            existing_columns = {
                row[1] for row in cur.execute("PRAGMA table_info(alert_outbox)").fetchall()
            }
            if "type" not in existing_columns:
                cur.execute("ALTER TABLE alert_outbox ADD COLUMN type TEXT NOT NULL DEFAULT 'alert'")
            if "severity" not in existing_columns:
                cur.execute("ALTER TABLE alert_outbox ADD COLUMN severity TEXT NOT NULL DEFAULT 'warning'")
            if "payload_json" not in existing_columns:
                cur.execute("ALTER TABLE alert_outbox ADD COLUMN payload_json TEXT NOT NULL DEFAULT '{}'")
            if "correlation_id" not in existing_columns:
                cur.execute("ALTER TABLE alert_outbox ADD COLUMN correlation_id TEXT NOT NULL DEFAULT ''")
            if "created_at" not in existing_columns:
                now_iso = datetime.now(timezone.utc).isoformat()
                cur.execute(f"ALTER TABLE alert_outbox ADD COLUMN created_at TEXT NOT NULL DEFAULT '{now_iso}'")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user_time ON reminder_events(user_id, scheduled_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_meals_user_time ON meal_records(user_id, captured_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_biomarkers_user_time_name ON biomarker_readings(user_id, measured_at, name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_user_time ON suggestion_records(user_id, created_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_alert_outbox_next_attempt ON alert_outbox(state, next_attempt_at)")
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
                (user_id, datetime.now(timezone.utc).isoformat(), json.dumps(payload)),
            )
            conn.commit()
        logger.info("save_recommendation user_id=%s payload_keys=%s", user_id, sorted(payload.keys()))

    def close(self) -> None:
        # Connections are opened per-operation; this keeps a symmetric app shutdown hook.
        return None

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
        logger.info("save_suggestion_record user_id=%s suggestion_id=%s", user_id, suggestion_id)
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
            logger.debug("get_suggestion_record_miss user_id=%s suggestion_id=%s", user_id, suggestion_id)
            return None
        item = json.loads(cast(str, row[0]))
        logger.debug("get_suggestion_record_hit user_id=%s suggestion_id=%s", user_id, suggestion_id)
        return item

    def enqueue_alert(self, message: AlertMessage) -> list[OutboxRecord]:
        created: list[OutboxRecord] = []
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            for sink in message.destinations:
                idempotency_key = f"{message.alert_id}:{sink}"
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO alert_outbox
                    (
                        alert_id, sink, type, severity, payload_json, correlation_id, created_at,
                        state, attempt_count, next_attempt_at, last_error, lease_owner, lease_until, idempotency_key
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.alert_id,
                        sink,
                        message.type,
                        message.severity,
                        json.dumps(message.payload),
                        message.correlation_id,
                        message.created_at.isoformat(),
                        "pending",
                        0,
                        now.isoformat(),
                        None,
                        None,
                        None,
                        idempotency_key,
                    ),
                )
                if cursor.rowcount != 1:
                    continue
                created.append(
                    OutboxRecord(
                        alert_id=message.alert_id,
                        sink=sink,
                        type=message.type,
                        severity=message.severity,
                        payload=message.payload,
                        correlation_id=message.correlation_id,
                        created_at=message.created_at,
                        state="pending",
                        attempt_count=0,
                        next_attempt_at=now,
                        idempotency_key=idempotency_key,
                    )
                )
            conn.commit()
        logger.info("enqueue_alert alert_id=%s sinks=%s", message.alert_id, message.destinations)
        return created

    def lease_alert_records(
        self,
        now: datetime,
        lease_owner: str,
        lease_seconds: int,
        limit: int,
        alert_id: str | None = None,
    ) -> list[OutboxRecord]:
        lease_until = now + timedelta(seconds=lease_seconds)
        query = """
                SELECT
                    alert_id, sink, type, severity, payload_json, correlation_id, created_at,
                    state, attempt_count, next_attempt_at, last_error, lease_owner, lease_until, idempotency_key
                FROM alert_outbox
                WHERE state IN ('pending', 'processing')
                  AND next_attempt_at <= ?
                  AND (lease_until IS NULL OR lease_until <= ?)
        """
        params: list[Any] = [now.isoformat(), now.isoformat()]
        if alert_id is not None:
            query += " AND alert_id = ?"
            params.append(alert_id)
        query += " ORDER BY next_attempt_at LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            leased: list[OutboxRecord] = []
            for row in rows:
                updated = conn.execute(
                    """
                    UPDATE alert_outbox
                    SET state = 'processing', lease_owner = ?, lease_until = ?
                    WHERE alert_id = ? AND sink = ?
                      AND state IN ('pending', 'processing')
                      AND next_attempt_at <= ?
                      AND (lease_until IS NULL OR lease_until <= ?)
                    """,
                    (
                        lease_owner,
                        lease_until.isoformat(),
                        row[0],
                        row[1],
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
                if updated.rowcount != 1:
                    continue
                leased.append(
                    OutboxRecord(
                        alert_id=row[0],
                        sink=row[1],
                        type=row[2],
                        severity=row[3],
                        payload=json.loads(row[4]),
                        correlation_id=row[5],
                        created_at=datetime.fromisoformat(row[6]),
                        state="processing",
                        attempt_count=row[8],
                        next_attempt_at=datetime.fromisoformat(row[9]),
                        last_error=row[10],
                        lease_owner=lease_owner,
                        lease_until=lease_until,
                        idempotency_key=row[13],
                    )
                )
            conn.commit()
        return leased

    def mark_alert_delivered(self, alert_id: str, sink: str, attempt_count: int | None = None) -> None:
        with sqlite3.connect(self.db_path) as conn:
            if attempt_count is None:
                conn.execute(
                    """
                    UPDATE alert_outbox
                    SET state='delivered', lease_owner=NULL, lease_until=NULL, last_error=NULL
                    WHERE alert_id=? AND sink=?
                    """,
                    (alert_id, sink),
                )
            else:
                conn.execute(
                    """
                    UPDATE alert_outbox
                    SET state='delivered', attempt_count=?, lease_owner=NULL, lease_until=NULL, last_error=NULL
                    WHERE alert_id=? AND sink=?
                    """,
                    (attempt_count, alert_id, sink),
                )
            conn.commit()

    def reschedule_alert(
        self,
        alert_id: str,
        sink: str,
        next_attempt_at: datetime,
        attempt_count: int,
        error: str,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE alert_outbox
                SET state='pending', attempt_count=?, next_attempt_at=?, last_error=?, lease_owner=NULL, lease_until=NULL
                WHERE alert_id=? AND sink=?
                """,
                (attempt_count, next_attempt_at.isoformat(), error, alert_id, sink),
            )
            conn.commit()

    def mark_alert_dead_letter(
        self,
        alert_id: str,
        sink: str,
        error: str,
        attempt_count: int | None = None,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            if attempt_count is None:
                conn.execute(
                    """
                    UPDATE alert_outbox
                    SET state='dead_letter', last_error=?, lease_owner=NULL, lease_until=NULL
                    WHERE alert_id=? AND sink=?
                    """,
                    (error, alert_id, sink),
                )
            else:
                conn.execute(
                    """
                    UPDATE alert_outbox
                    SET state='dead_letter', attempt_count=?, last_error=?, lease_owner=NULL, lease_until=NULL
                    WHERE alert_id=? AND sink=?
                    """,
                    (attempt_count, error, alert_id, sink),
                )
            conn.commit()

    def list_alert_records(self, alert_id: str | None = None) -> list[OutboxRecord]:
        query = (
            "SELECT "
            "alert_id, sink, type, severity, payload_json, correlation_id, created_at, "
            "state, attempt_count, next_attempt_at, last_error, lease_owner, lease_until, idempotency_key "
            "FROM alert_outbox"
        )
        params: tuple[str, ...] = ()
        if alert_id is not None:
            query += " WHERE alert_id = ?"
            params = (alert_id,)
        query += " ORDER BY next_attempt_at"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        out: list[OutboxRecord] = []
        for row in rows:
            out.append(
                OutboxRecord(
                    alert_id=row[0],
                    sink=row[1],
                    type=row[2],
                    severity=row[3],
                    payload=json.loads(row[4]),
                    correlation_id=row[5],
                    created_at=datetime.fromisoformat(row[6]),
                    state=row[7],
                    attempt_count=row[8],
                    next_attempt_at=datetime.fromisoformat(row[9]),
                    last_error=row[10],
                    lease_owner=row[11],
                    lease_until=datetime.fromisoformat(row[12]) if row[12] else None,
                    idempotency_key=row[13],
                )
            )
        return out
