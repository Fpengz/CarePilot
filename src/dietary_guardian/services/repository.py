import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.meal import MealState
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.models.medication import MedicationRegimen, ReminderEvent
from dietary_guardian.models.mobility import MobilityReminderSettings
from dietary_guardian.models.report import BiomarkerReading
from dietary_guardian.models.alerting import AlertMessage, OutboxRecord
from dietary_guardian.models.health_profile import HealthProfileRecord
from dietary_guardian.models.health_profile_onboarding import HealthProfileOnboardingState
from dietary_guardian.models.clinical_card import ClinicalCardRecord
from dietary_guardian.models.medication_tracking import MedicationAdherenceEvent
from dietary_guardian.models.recommendation_agent import MealCatalogItem, PreferenceSnapshot, RecommendationInteraction
from dietary_guardian.models.reminder_notifications import (
    ReminderNotificationEndpoint,
    ReminderNotificationLogEntry,
    ReminderNotificationPreference,
    ScheduledReminderNotification,
)
from dietary_guardian.services.meal_catalog_service import DEFAULT_MEAL_CATALOG
from dietary_guardian.models.symptom import SymptomCheckIn, SymptomSafety
from dietary_guardian.models.tool_policy import ToolRolePolicyRecord
from dietary_guardian.models.user import MealSlot
from dietary_guardian.models.workflow_contract_snapshot import WorkflowContractSnapshotRecord

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
                    reminder_type TEXT NOT NULL DEFAULT 'medication',
                    title TEXT NOT NULL DEFAULT 'Medication Reminder',
                    body TEXT,
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
                CREATE TABLE IF NOT EXISTS health_profiles (
                    user_id TEXT PRIMARY KEY,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS health_profile_onboarding_states (
                    user_id TEXT PRIMARY KEY,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS meal_catalog (
                    meal_id TEXT PRIMARY KEY,
                    locale TEXT NOT NULL,
                    slot TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS recommendation_interactions (
                    interaction_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    recommendation_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    slot TEXT NOT NULL,
                    source_meal_id TEXT,
                    selected_meal_id TEXT,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS preference_snapshots (
                    user_id TEXT PRIMARY KEY,
                    updated_at TEXT NOT NULL,
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
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS reminder_notification_preferences (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    scope_type TEXT NOT NULL,
                    scope_key TEXT,
                    channel TEXT NOT NULL,
                    offset_minutes INTEGER NOT NULL,
                    enabled INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, scope_type, scope_key, channel, offset_minutes)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_notifications (
                    id TEXT PRIMARY KEY,
                    reminder_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    trigger_at TEXT NOT NULL,
                    offset_minutes INTEGER NOT NULL,
                    preference_id TEXT,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    next_attempt_at TEXT,
                    queued_at TEXT,
                    delivered_at TEXT,
                    last_error TEXT,
                    payload_json TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_logs (
                    id TEXT PRIMARY KEY,
                    scheduled_notification_id TEXT NOT NULL,
                    reminder_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    error_message TEXT,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS reminder_notification_endpoints (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    verified INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, channel)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS mobility_reminder_settings (
                    user_id TEXT PRIMARY KEY,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS medication_adherence_events (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    regimen_id TEXT NOT NULL,
                    reminder_id TEXT,
                    status TEXT NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    taken_at TEXT,
                    source TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS symptom_checkins (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    severity INTEGER NOT NULL,
                    symptom_codes_json TEXT NOT NULL,
                    free_text TEXT,
                    context_json TEXT NOT NULL,
                    safety_json TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS clinical_cards (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    format TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tool_role_policies (
                    id TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    effect TEXT NOT NULL,
                    conditions_json TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    enabled INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_contract_snapshots (
                    id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL UNIQUE,
                    contract_hash TEXT NOT NULL,
                    source TEXT NOT NULL,
                    workflows_json TEXT NOT NULL,
                    agents_json TEXT NOT NULL,
                    created_by TEXT,
                    created_at TEXT NOT NULL
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
            reminder_event_columns = {
                row[1] for row in cur.execute("PRAGMA table_info(reminder_events)").fetchall()
            }
            if "reminder_type" not in reminder_event_columns:
                cur.execute("ALTER TABLE reminder_events ADD COLUMN reminder_type TEXT NOT NULL DEFAULT 'medication'")
            if "title" not in reminder_event_columns:
                cur.execute("ALTER TABLE reminder_events ADD COLUMN title TEXT NOT NULL DEFAULT 'Medication Reminder'")
            if "body" not in reminder_event_columns:
                cur.execute("ALTER TABLE reminder_events ADD COLUMN body TEXT")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user_time ON reminder_events(user_id, scheduled_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_meals_user_time ON meal_records(user_id, captured_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_biomarkers_user_time_name ON biomarker_readings(user_id, measured_at, name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_user_time ON suggestion_records(user_id, created_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_health_profiles_updated_at ON health_profiles(updated_at DESC)")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_health_profile_onboarding_updated_at ON health_profile_onboarding_states(updated_at DESC)"
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_meal_catalog_locale_slot ON meal_catalog(locale, slot)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_recommendation_interactions_user_time ON recommendation_interactions(user_id, created_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_preference_snapshots_updated_at ON preference_snapshots(updated_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_alert_outbox_next_attempt ON alert_outbox(state, next_attempt_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_reminder_notification_preferences_user_scope ON reminder_notification_preferences(user_id, scope_type, scope_key)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_due ON scheduled_notifications(status, trigger_at, next_attempt_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_reminder_id ON scheduled_notifications(reminder_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_notification_logs_reminder_created ON notification_logs(reminder_id, created_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_reminder_notification_endpoints_user_channel ON reminder_notification_endpoints(user_id, channel)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_adherence_user_time ON medication_adherence_events(user_id, scheduled_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_symptom_checkins_user_time ON symptom_checkins(user_id, recorded_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_clinical_cards_user_created ON clinical_cards(user_id, created_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tool_role_policies_lookup ON tool_role_policies(role, agent_id, tool_name, enabled, priority DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_workflow_contract_snapshots_created ON workflow_contract_snapshots(created_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_workflow_contract_snapshots_hash ON workflow_contract_snapshots(contract_hash)")
            conn.commit()
        self._seed_meal_catalog()
        logger.info("repository_schema_ready db_path=%s", self.db_path)

    def _seed_meal_catalog(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute("SELECT COUNT(*) FROM meal_catalog").fetchone()
            if existing is not None and int(existing[0]) > 0:
                return
            for item in DEFAULT_MEAL_CATALOG:
                payload = item.model_dump(mode="json")
                conn.execute(
                    """
                    INSERT INTO meal_catalog (meal_id, locale, slot, active, payload_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (item.meal_id, item.locale, item.slot, int(item.active), json.dumps(payload)),
                )
            conn.commit()

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

    def save_reminder_event(self, event: ReminderEvent) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO reminder_events
                (id, user_id, reminder_type, title, body, medication_name, scheduled_at, slot, dosage_text, status, meal_confirmation, sent_at, ack_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.user_id,
                    event.reminder_type,
                    event.title,
                    event.body,
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
                SELECT id, user_id, reminder_type, title, body, medication_name, scheduled_at, slot, dosage_text, status, meal_confirmation, sent_at, ack_at
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
            reminder_type=row[2],
            title=row[3],
            body=row[4],
            medication_name=row[5],
            scheduled_at=datetime.fromisoformat(row[6]),
            slot=row[7],
            dosage_text=row[8],
            status=row[9],
            meal_confirmation=row[10],
            sent_at=datetime.fromisoformat(row[11]) if row[11] else None,
            ack_at=datetime.fromisoformat(row[12]) if row[12] else None,
        )

    def list_reminder_events(self, user_id: str) -> list[ReminderEvent]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, reminder_type, title, body, medication_name, scheduled_at, slot, dosage_text, status, meal_confirmation, sent_at, ack_at
                FROM reminder_events WHERE user_id = ? ORDER BY scheduled_at
                """,
                (user_id,),
            ).fetchall()
        events = [
            ReminderEvent(
                id=r[0],
                user_id=r[1],
                reminder_type=r[2],
                title=r[3],
                body=r[4],
                medication_name=r[5],
                scheduled_at=datetime.fromisoformat(r[6]),
                slot=r[7],
                dosage_text=r[8],
                status=r[9],
                meal_confirmation=r[10],
                sent_at=datetime.fromisoformat(r[11]) if r[11] else None,
                ack_at=datetime.fromisoformat(r[12]) if r[12] else None,
            )
            for r in rows
        ]
        logger.debug("list_reminder_events user_id=%s count=%s", user_id, len(events))
        return events

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

    def replace_reminder_notification_preferences(
        self,
        *,
        user_id: str,
        scope_type: str,
        scope_key: str | None,
        preferences: list[ReminderNotificationPreference],
    ) -> list[ReminderNotificationPreference]:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                DELETE FROM reminder_notification_preferences
                WHERE user_id = ? AND scope_type = ? AND (
                    (scope_key IS NULL AND ? IS NULL) OR scope_key = ?
                )
                """,
                (user_id, scope_type, scope_key, scope_key),
            )
            for preference in preferences:
                conn.execute(
                    """
                    INSERT INTO reminder_notification_preferences
                    (id, user_id, scope_type, scope_key, channel, offset_minutes, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        preference.id,
                        preference.user_id,
                        preference.scope_type,
                        preference.scope_key,
                        preference.channel,
                        preference.offset_minutes,
                        int(preference.enabled),
                        preference.created_at.isoformat(),
                        preference.updated_at.isoformat(),
                    ),
                )
            conn.commit()
        return self.list_reminder_notification_preferences(user_id=user_id, scope_type=scope_type, scope_key=scope_key)

    def list_reminder_notification_preferences(
        self,
        *,
        user_id: str,
        scope_type: str | None = None,
        scope_key: str | None = None,
    ) -> list[ReminderNotificationPreference]:
        query = (
            "SELECT id, user_id, scope_type, scope_key, channel, offset_minutes, enabled, created_at, updated_at "
            "FROM reminder_notification_preferences WHERE user_id = ?"
        )
        params: list[Any] = [user_id]
        if scope_type is not None:
            query += " AND scope_type = ?"
            params.append(scope_type)
            if scope_key is None:
                query += " AND scope_key IS NULL"
            else:
                query += " AND scope_key = ?"
                params.append(scope_key)
        query += " ORDER BY scope_type, scope_key, offset_minutes, channel"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            ReminderNotificationPreference(
                id=row[0],
                user_id=row[1],
                scope_type=row[2],
                scope_key=row[3],
                channel=row[4],
                offset_minutes=row[5],
                enabled=bool(row[6]),
                created_at=datetime.fromisoformat(row[7]),
                updated_at=datetime.fromisoformat(row[8]),
            )
            for row in rows
        ]

    def save_scheduled_notification(self, item: ScheduledReminderNotification) -> ScheduledReminderNotification:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO scheduled_notifications
                (
                    id, reminder_id, user_id, channel, trigger_at, offset_minutes, preference_id,
                    status, attempt_count, next_attempt_at, queued_at, delivered_at, last_error,
                    payload_json, idempotency_key, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    item.reminder_id,
                    item.user_id,
                    item.channel,
                    item.trigger_at.isoformat(),
                    item.offset_minutes,
                    item.preference_id,
                    item.status,
                    item.attempt_count,
                    item.next_attempt_at.isoformat() if item.next_attempt_at else None,
                    item.queued_at.isoformat() if item.queued_at else None,
                    item.delivered_at.isoformat() if item.delivered_at else None,
                    item.last_error,
                    json.dumps(item.payload),
                    item.idempotency_key,
                    item.created_at.isoformat(),
                    item.updated_at.isoformat(),
                ),
            )
            conn.commit()
        existing = self.get_scheduled_notification(item.id)
        if existing is None:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT id FROM scheduled_notifications WHERE idempotency_key = ?",
                    (item.idempotency_key,),
                ).fetchone()
            if row is not None:
                existing = self.get_scheduled_notification(str(row[0]))
        if existing is None:
            raise RuntimeError(f"failed to persist scheduled notification {item.id}")
        return existing

    def get_scheduled_notification(self, notification_id: str) -> ScheduledReminderNotification | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, reminder_id, user_id, channel, trigger_at, offset_minutes, preference_id, status,
                       attempt_count, next_attempt_at, queued_at, delivered_at, last_error, payload_json,
                       idempotency_key, created_at, updated_at
                FROM scheduled_notifications
                WHERE id = ?
                """,
                (notification_id,),
            ).fetchone()
        if row is None:
            return None
        return ScheduledReminderNotification(
            id=row[0],
            reminder_id=row[1],
            user_id=row[2],
            channel=row[3],
            trigger_at=datetime.fromisoformat(row[4]),
            offset_minutes=row[5],
            preference_id=row[6],
            status=row[7],
            attempt_count=row[8],
            next_attempt_at=datetime.fromisoformat(row[9]) if row[9] else None,
            queued_at=datetime.fromisoformat(row[10]) if row[10] else None,
            delivered_at=datetime.fromisoformat(row[11]) if row[11] else None,
            last_error=row[12],
            payload=json.loads(cast(str, row[13])),
            idempotency_key=row[14],
            created_at=datetime.fromisoformat(row[15]),
            updated_at=datetime.fromisoformat(row[16]),
        )

    def list_scheduled_notifications(
        self,
        *,
        reminder_id: str | None = None,
        user_id: str | None = None,
    ) -> list[ScheduledReminderNotification]:
        query = (
            "SELECT id, reminder_id, user_id, channel, trigger_at, offset_minutes, preference_id, status, "
            "attempt_count, next_attempt_at, queued_at, delivered_at, last_error, payload_json, "
            "idempotency_key, created_at, updated_at FROM scheduled_notifications WHERE 1=1"
        )
        params: list[Any] = []
        if reminder_id is not None:
            query += " AND reminder_id = ?"
            params.append(reminder_id)
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        query += " ORDER BY trigger_at, channel"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            ScheduledReminderNotification(
                id=row[0],
                reminder_id=row[1],
                user_id=row[2],
                channel=row[3],
                trigger_at=datetime.fromisoformat(row[4]),
                offset_minutes=row[5],
                preference_id=row[6],
                status=row[7],
                attempt_count=row[8],
                next_attempt_at=datetime.fromisoformat(row[9]) if row[9] else None,
                queued_at=datetime.fromisoformat(row[10]) if row[10] else None,
                delivered_at=datetime.fromisoformat(row[11]) if row[11] else None,
                last_error=row[12],
                payload=json.loads(cast(str, row[13])),
                idempotency_key=row[14],
                created_at=datetime.fromisoformat(row[15]),
                updated_at=datetime.fromisoformat(row[16]),
            )
            for row in rows
        ]

    def lease_due_scheduled_notifications(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> list[ScheduledReminderNotification]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id
                FROM scheduled_notifications
                WHERE status IN ('pending', 'retry_scheduled')
                  AND COALESCE(next_attempt_at, trigger_at) <= ?
                ORDER BY COALESCE(next_attempt_at, trigger_at), channel
                LIMIT ?
                """,
                (now.isoformat(), limit),
            ).fetchall()
            leased: list[ScheduledReminderNotification] = []
            for (notification_id,) in rows:
                updated = conn.execute(
                    """
                    UPDATE scheduled_notifications
                    SET status = 'queued', queued_at = ?, updated_at = ?, last_error = NULL
                    WHERE id = ? AND status IN ('pending', 'retry_scheduled')
                    """,
                    (now.isoformat(), now.isoformat(), notification_id),
                )
                if updated.rowcount != 1:
                    continue
                record = self.get_scheduled_notification(str(notification_id))
                if record is not None:
                    leased.append(record)
            conn.commit()
        return leased

    def set_scheduled_notification_trigger_at(self, notification_id: str, trigger_at: datetime) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE scheduled_notifications
                SET trigger_at = ?, next_attempt_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (trigger_at.isoformat(), trigger_at.isoformat(), datetime.now(timezone.utc).isoformat(), notification_id),
            )
            conn.commit()

    def mark_scheduled_notification_processing(self, notification_id: str, attempt_count: int) -> None:
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE scheduled_notifications
                SET status = 'processing', attempt_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (attempt_count, now.isoformat(), notification_id),
            )
            conn.commit()

    def mark_scheduled_notification_delivered(self, notification_id: str, attempt_count: int) -> None:
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE scheduled_notifications
                SET status = 'delivered', attempt_count = ?, delivered_at = ?, updated_at = ?, last_error = NULL
                WHERE id = ?
                """,
                (attempt_count, now.isoformat(), now.isoformat(), notification_id),
            )
            conn.commit()

    def reschedule_scheduled_notification(
        self,
        notification_id: str,
        *,
        attempt_count: int,
        next_attempt_at: datetime,
        error: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE scheduled_notifications
                SET status = 'retry_scheduled', attempt_count = ?, next_attempt_at = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (attempt_count, next_attempt_at.isoformat(), error, now.isoformat(), notification_id),
            )
            conn.commit()

    def mark_scheduled_notification_dead_letter(
        self,
        notification_id: str,
        *,
        attempt_count: int,
        error: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE scheduled_notifications
                SET status = 'dead_letter', attempt_count = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (attempt_count, error, now.isoformat(), notification_id),
            )
            conn.commit()

    def cancel_scheduled_notifications_for_reminder(self, reminder_id: str) -> int:
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                """
                UPDATE scheduled_notifications
                SET status = 'cancelled', updated_at = ?
                WHERE reminder_id = ? AND status IN ('pending', 'queued', 'processing', 'retry_scheduled')
                """,
                (now.isoformat(), reminder_id),
            )
            conn.commit()
        return int(result.rowcount)

    def append_notification_log(self, entry: ReminderNotificationLogEntry) -> ReminderNotificationLogEntry:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO notification_logs
                (id, scheduled_notification_id, reminder_id, user_id, channel, attempt_number, event_type, error_message, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.scheduled_notification_id,
                    entry.reminder_id,
                    entry.user_id,
                    entry.channel,
                    entry.attempt_number,
                    entry.event_type,
                    entry.error_message,
                    json.dumps(entry.metadata),
                    entry.created_at.isoformat(),
                ),
            )
            conn.commit()
        return entry

    def replace_reminder_notification_endpoints(
        self,
        *,
        user_id: str,
        endpoints: list[ReminderNotificationEndpoint],
    ) -> list[ReminderNotificationEndpoint]:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM reminder_notification_endpoints WHERE user_id = ?",
                (user_id,),
            )
            for endpoint in endpoints:
                conn.execute(
                    """
                    INSERT INTO reminder_notification_endpoints
                    (id, user_id, channel, destination, verified, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        endpoint.id,
                        endpoint.user_id,
                        endpoint.channel,
                        endpoint.destination,
                        int(endpoint.verified),
                        endpoint.created_at.isoformat(),
                        endpoint.updated_at.isoformat(),
                    ),
                )
            conn.commit()
        return self.list_reminder_notification_endpoints(user_id=user_id)

    def list_reminder_notification_endpoints(self, *, user_id: str) -> list[ReminderNotificationEndpoint]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, channel, destination, verified, created_at, updated_at
                FROM reminder_notification_endpoints
                WHERE user_id = ?
                ORDER BY channel
                """,
                (user_id,),
            ).fetchall()
        return [
            ReminderNotificationEndpoint(
                id=row[0],
                user_id=row[1],
                channel=row[2],
                destination=row[3],
                verified=bool(row[4]),
                created_at=datetime.fromisoformat(row[5]),
                updated_at=datetime.fromisoformat(row[6]),
            )
            for row in rows
        ]

    def get_reminder_notification_endpoint(
        self,
        *,
        user_id: str,
        channel: str,
    ) -> ReminderNotificationEndpoint | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, user_id, channel, destination, verified, created_at, updated_at
                FROM reminder_notification_endpoints
                WHERE user_id = ? AND channel = ?
                """,
                (user_id, channel),
            ).fetchone()
        if row is None:
            return None
        return ReminderNotificationEndpoint(
            id=row[0],
            user_id=row[1],
            channel=row[2],
            destination=row[3],
            verified=bool(row[4]),
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6]),
        )

    def list_notification_logs(
        self,
        *,
        reminder_id: str | None = None,
        scheduled_notification_id: str | None = None,
    ) -> list[ReminderNotificationLogEntry]:
        query = (
            "SELECT id, scheduled_notification_id, reminder_id, user_id, channel, attempt_number, event_type, "
            "error_message, metadata_json, created_at FROM notification_logs WHERE 1=1"
        )
        params: list[Any] = []
        if reminder_id is not None:
            query += " AND reminder_id = ?"
            params.append(reminder_id)
        if scheduled_notification_id is not None:
            query += " AND scheduled_notification_id = ?"
            params.append(scheduled_notification_id)
        query += " ORDER BY created_at"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            ReminderNotificationLogEntry(
                id=row[0],
                scheduled_notification_id=row[1],
                reminder_id=row[2],
                user_id=row[3],
                channel=row[4],
                attempt_number=row[5],
                event_type=row[6],
                error_message=row[7],
                metadata=json.loads(cast(str, row[8])),
                created_at=datetime.fromisoformat(row[9]),
            )
            for row in rows
        ]

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

    def get_meal_record(self, user_id: str, meal_id: str) -> MealRecognitionRecord | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, user_id, captured_at, source, meal_state_json, analysis_version, multi_item_count
                FROM meal_records WHERE user_id = ? AND id = ?
                """,
                (user_id, meal_id),
            ).fetchone()
        if row is None:
            logger.debug("get_meal_record_miss user_id=%s meal_id=%s", user_id, meal_id)
            return None
        return MealRecognitionRecord(
            id=row[0],
            user_id=row[1],
            captured_at=datetime.fromisoformat(row[2]),
            source=row[3],
            meal_state=MealState.model_validate_json(row[4]),
            analysis_version=row[5],
            multi_item_count=row[6],
        )

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

    def save_tool_role_policy(self, record: ToolRolePolicyRecord) -> ToolRolePolicyRecord:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO tool_role_policies
                (id, role, agent_id, tool_name, effect, conditions_json, priority, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    role = excluded.role,
                    agent_id = excluded.agent_id,
                    tool_name = excluded.tool_name,
                    effect = excluded.effect,
                    conditions_json = excluded.conditions_json,
                    priority = excluded.priority,
                    enabled = excluded.enabled,
                    updated_at = excluded.updated_at
                """,
                (
                    record.id,
                    record.role,
                    record.agent_id,
                    record.tool_name,
                    record.effect,
                    json.dumps(record.conditions),
                    record.priority,
                    1 if record.enabled else 0,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
            conn.commit()
        return record

    def list_tool_role_policies(
        self,
        *,
        role: str | None = None,
        agent_id: str | None = None,
        tool_name: str | None = None,
        enabled_only: bool = False,
    ) -> list[ToolRolePolicyRecord]:
        query = (
            "SELECT id, role, agent_id, tool_name, effect, conditions_json, priority, enabled, created_at, updated_at "
            "FROM tool_role_policies WHERE 1=1"
        )
        params: list[Any] = []
        if role is not None:
            query += " AND role = ?"
            params.append(role)
        if agent_id is not None:
            query += " AND agent_id = ?"
            params.append(agent_id)
        if tool_name is not None:
            query += " AND tool_name = ?"
            params.append(tool_name)
        if enabled_only:
            query += " AND enabled = 1"
        query += " ORDER BY priority DESC, updated_at DESC, id"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            ToolRolePolicyRecord(
                id=row[0],
                role=row[1],
                agent_id=row[2],
                tool_name=row[3],
                effect=row[4],
                conditions=json.loads(row[5]),
                priority=int(row[6]),
                enabled=bool(row[7]),
                created_at=datetime.fromisoformat(row[8]),
                updated_at=datetime.fromisoformat(row[9]),
            )
            for row in rows
        ]

    def get_tool_role_policy(self, policy_id: str) -> ToolRolePolicyRecord | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, role, agent_id, tool_name, effect, conditions_json, priority, enabled, created_at, updated_at
                FROM tool_role_policies
                WHERE id = ?
                """,
                (policy_id,),
            ).fetchone()
        if row is None:
            return None
        return ToolRolePolicyRecord(
            id=row[0],
            role=row[1],
            agent_id=row[2],
            tool_name=row[3],
            effect=row[4],
            conditions=json.loads(row[5]),
            priority=int(row[6]),
            enabled=bool(row[7]),
            created_at=datetime.fromisoformat(row[8]),
            updated_at=datetime.fromisoformat(row[9]),
        )

    def save_workflow_contract_snapshot(
        self,
        snapshot: WorkflowContractSnapshotRecord,
    ) -> WorkflowContractSnapshotRecord:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO workflow_contract_snapshots
                (id, version, contract_hash, source, workflows_json, agents_json, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    version = excluded.version,
                    contract_hash = excluded.contract_hash,
                    source = excluded.source,
                    workflows_json = excluded.workflows_json,
                    agents_json = excluded.agents_json,
                    created_by = excluded.created_by,
                    created_at = excluded.created_at
                """,
                (
                    snapshot.id,
                    snapshot.version,
                    snapshot.contract_hash,
                    snapshot.source,
                    json.dumps([item.model_dump(mode="json") for item in snapshot.workflows]),
                    json.dumps([item.model_dump(mode="json") for item in snapshot.agents]),
                    snapshot.created_by,
                    snapshot.created_at.isoformat(),
                ),
            )
            conn.commit()
        return snapshot

    def list_workflow_contract_snapshots(self, *, limit: int = 50) -> list[WorkflowContractSnapshotRecord]:
        bounded_limit = max(1, min(limit, 200))
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, version, contract_hash, source, workflows_json, agents_json, created_by, created_at
                FROM workflow_contract_snapshots
                ORDER BY version DESC
                LIMIT ?
                """,
                (bounded_limit,),
            ).fetchall()
        return [
            WorkflowContractSnapshotRecord(
                id=row[0],
                version=int(row[1]),
                contract_hash=row[2],
                source=row[3],
                workflows=json.loads(row[4]),
                agents=json.loads(row[5]),
                created_by=row[6],
                created_at=datetime.fromisoformat(row[7]),
            )
            for row in rows
        ]

    def get_workflow_contract_snapshot(self, *, version: int) -> WorkflowContractSnapshotRecord | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, version, contract_hash, source, workflows_json, agents_json, created_by, created_at
                FROM workflow_contract_snapshots
                WHERE version = ?
                """,
                (version,),
            ).fetchone()
        if row is None:
            return None
        return WorkflowContractSnapshotRecord(
            id=row[0],
            version=int(row[1]),
            contract_hash=row[2],
            source=row[3],
            workflows=json.loads(row[4]),
            agents=json.loads(row[5]),
            created_by=row[6],
            created_at=datetime.fromisoformat(row[7]),
        )

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

    def get_mobility_reminder_settings(self, user_id: str) -> MobilityReminderSettings | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM mobility_reminder_settings
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return MobilityReminderSettings.model_validate_json(cast(str, row[0]))

    def save_mobility_reminder_settings(self, settings: MobilityReminderSettings) -> MobilityReminderSettings:
        payload = settings.model_dump(mode="json")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO mobility_reminder_settings (user_id, updated_at, payload_json)
                VALUES (?, ?, ?)
                """,
                (settings.user_id, str(payload["updated_at"]), json.dumps(payload)),
            )
            conn.commit()
        return settings

    def list_meal_catalog_items(self, *, locale: str, slot: str | None = None, limit: int = 100) -> list[MealCatalogItem]:
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

    def save_recommendation_interaction(self, interaction: RecommendationInteraction) -> RecommendationInteraction:
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

    def list_recommendation_interactions(self, user_id: str, *, limit: int = 200) -> list[RecommendationInteraction]:
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
                (snapshot.user_id, snapshot.updated_at.isoformat(), json.dumps(payload)),
            )
            conn.commit()
        logger.info(
            "save_preference_snapshot user_id=%s interactions=%s",
            snapshot.user_id,
            snapshot.interaction_count,
        )
        return snapshot

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
