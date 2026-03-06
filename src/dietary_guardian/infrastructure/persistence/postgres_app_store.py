from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from dietary_guardian.infrastructure.persistence.postgres_schema import ensure_postgres_app_schema
from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.alerting import AlertMessage, OutboxRecord
from dietary_guardian.models.agent_runtime import AgentContract, WorkflowRuntimeContract
from dietary_guardian.models.clinical_card import ClinicalCardRecord
from dietary_guardian.models.health_profile import HealthProfileRecord
from dietary_guardian.models.health_profile_onboarding import HealthProfileOnboardingState
from dietary_guardian.models.meal import MealState
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.models.medication import MedicationRegimen, ReminderEvent
from dietary_guardian.models.medication_tracking import MedicationAdherenceEvent
from dietary_guardian.models.mobility import MobilityReminderSettings
from dietary_guardian.models.recommendation_agent import MealCatalogItem, PreferenceSnapshot, RecommendationInteraction
from dietary_guardian.models.reminder_notifications import (
    ReminderNotificationEndpoint,
    ReminderNotificationLogEntry,
    ReminderNotificationPreference,
    ScheduledReminderNotification,
)
from dietary_guardian.models.report import BiomarkerReading
from dietary_guardian.models.symptom import SymptomCheckIn, SymptomSafety
from dietary_guardian.models.tool_policy import ToolRolePolicyRecord
from dietary_guardian.models.user import MealSlot
from dietary_guardian.models.workflow_contract_snapshot import WorkflowContractSnapshotRecord
from dietary_guardian.services.meal_catalog_service import DEFAULT_MEAL_CATALOG

logger = get_logger(__name__)
def _load_psycopg_module() -> Any:
    try:
        import psycopg
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "psycopg package is required for APP_DATA_BACKEND=postgres. Run `uv sync` after updating dependencies."
        ) from exc
    return psycopg


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    raise TypeError(f"Unsupported datetime value: {value!r}")


def _json_payload(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _model_from_payload(model_type: Any, payload: Any) -> Any:
    if isinstance(payload, (str, bytes, bytearray)):
        return model_type.model_validate_json(payload)
    return model_type.model_validate(payload)


class PostgresAppStore:
    def __init__(self, *, dsn: str) -> None:
        self._psycopg = _load_psycopg_module()
        self._dsn = dsn
        self._jsonb = self._psycopg.types.json.Jsonb
        with self._connect() as conn:
            ensure_postgres_app_schema(conn)
        self._seed_meal_catalog()

    def _connect(self) -> Any:
        return self._psycopg.connect(self._dsn, autocommit=True)

    def _seed_meal_catalog(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM meal_catalog")
            existing = cur.fetchone()
            if existing is not None and int(existing[0]) > 0:
                return
            for item in DEFAULT_MEAL_CATALOG:
                payload = item.model_dump(mode="json")
                cur.execute(
                    """
                    INSERT INTO meal_catalog (meal_id, locale, slot, active, payload_json)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (meal_id) DO NOTHING
                    """,
                    (item.meal_id, item.locale, item.slot, item.active, self._jsonb(payload)),
                )

    def save_medication_regimen(self, regimen: MedicationRegimen) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO medication_regimens
                (id, user_id, medication_name, dosage_text, timing_type, offset_minutes, slot_scope_json, fixed_time, max_daily_doses, active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    medication_name = EXCLUDED.medication_name,
                    dosage_text = EXCLUDED.dosage_text,
                    timing_type = EXCLUDED.timing_type,
                    offset_minutes = EXCLUDED.offset_minutes,
                    slot_scope_json = EXCLUDED.slot_scope_json,
                    fixed_time = EXCLUDED.fixed_time,
                    max_daily_doses = EXCLUDED.max_daily_doses,
                    active = EXCLUDED.active
                """,
                (
                    regimen.id,
                    regimen.user_id,
                    regimen.medication_name,
                    regimen.dosage_text,
                    regimen.timing_type,
                    regimen.offset_minutes,
                    self._jsonb(regimen.slot_scope),
                    regimen.fixed_time,
                    regimen.max_daily_doses,
                    regimen.active,
                ),
            )
        logger.debug("save_medication_regimen id=%s user_id=%s", regimen.id, regimen.user_id)

    def list_medication_regimens(self, user_id: str, *, active_only: bool = False) -> list[MedicationRegimen]:
        query = (
            "SELECT id, user_id, medication_name, dosage_text, timing_type, offset_minutes, slot_scope_json, fixed_time, max_daily_doses, active "
            "FROM medication_regimens WHERE user_id = %s"
        )
        params: list[Any] = [user_id]
        if active_only:
            query += " AND active = TRUE"
        query += " ORDER BY medication_name, id"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
        return [
            MedicationRegimen(
                id=row[0],
                user_id=row[1],
                medication_name=row[2],
                dosage_text=row[3],
                timing_type=row[4],
                offset_minutes=int(row[5]),
                slot_scope=cast(list[MealSlot], _json_payload(row[6])),
                fixed_time=row[7],
                max_daily_doses=int(row[8]),
                active=bool(row[9]),
            )
            for row in rows
        ]

    def get_medication_regimen(self, *, user_id: str, regimen_id: str) -> MedicationRegimen | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, medication_name, dosage_text, timing_type, offset_minutes, slot_scope_json, fixed_time, max_daily_doses, active
                FROM medication_regimens
                WHERE user_id = %s AND id = %s
                """,
                (user_id, regimen_id),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return MedicationRegimen(
            id=row[0],
            user_id=row[1],
            medication_name=row[2],
            dosage_text=row[3],
            timing_type=row[4],
            offset_minutes=int(row[5]),
            slot_scope=cast(list[MealSlot], _json_payload(row[6])),
            fixed_time=row[7],
            max_daily_doses=int(row[8]),
            active=bool(row[9]),
        )

    def delete_medication_regimen(self, *, user_id: str, regimen_id: str) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM medication_regimens WHERE user_id = %s AND id = %s",
                (user_id, regimen_id),
            )
            deleted = cur.rowcount
        return deleted == 1

    def save_reminder_event(self, event: ReminderEvent) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO reminder_events
                (id, user_id, reminder_type, title, body, medication_name, scheduled_at, slot, dosage_text, status, meal_confirmation, sent_at, ack_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    reminder_type = EXCLUDED.reminder_type,
                    title = EXCLUDED.title,
                    body = EXCLUDED.body,
                    medication_name = EXCLUDED.medication_name,
                    scheduled_at = EXCLUDED.scheduled_at,
                    slot = EXCLUDED.slot,
                    dosage_text = EXCLUDED.dosage_text,
                    status = EXCLUDED.status,
                    meal_confirmation = EXCLUDED.meal_confirmation,
                    sent_at = EXCLUDED.sent_at,
                    ack_at = EXCLUDED.ack_at
                """,
                (
                    event.id,
                    event.user_id,
                    event.reminder_type,
                    event.title,
                    event.body,
                    event.medication_name,
                    event.scheduled_at,
                    event.slot,
                    event.dosage_text,
                    event.status,
                    event.meal_confirmation,
                    event.sent_at,
                    event.ack_at,
                ),
            )
        logger.debug("save_reminder_event id=%s user_id=%s status=%s", event.id, event.user_id, event.status)

    def get_reminder_event(self, event_id: str) -> ReminderEvent | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, reminder_type, title, body, medication_name, scheduled_at, slot, dosage_text, status, meal_confirmation, sent_at, ack_at
                FROM reminder_events
                WHERE id = %s
                """,
                (event_id,),
            )
            row = cur.fetchone()
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
            scheduled_at=row[6],
            slot=row[7],
            dosage_text=row[8],
            status=row[9],
            meal_confirmation=row[10],
            sent_at=row[11],
            ack_at=row[12],
        )

    def list_reminder_events(self, user_id: str) -> list[ReminderEvent]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, reminder_type, title, body, medication_name, scheduled_at, slot, dosage_text, status, meal_confirmation, sent_at, ack_at
                FROM reminder_events
                WHERE user_id = %s
                ORDER BY scheduled_at
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        events = [
            ReminderEvent(
                id=row[0],
                user_id=row[1],
                reminder_type=row[2],
                title=row[3],
                body=row[4],
                medication_name=row[5],
                scheduled_at=row[6],
                slot=row[7],
                dosage_text=row[8],
                status=row[9],
                meal_confirmation=row[10],
                sent_at=row[11],
                ack_at=row[12],
            )
            for row in rows
        ]
        logger.debug("list_reminder_events user_id=%s count=%s", user_id, len(events))
        return events

    def save_medication_adherence_event(self, event: MedicationAdherenceEvent) -> MedicationAdherenceEvent:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO medication_adherence_events
                (id, user_id, regimen_id, reminder_id, status, scheduled_at, taken_at, source, metadata_json, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    regimen_id = EXCLUDED.regimen_id,
                    reminder_id = EXCLUDED.reminder_id,
                    status = EXCLUDED.status,
                    scheduled_at = EXCLUDED.scheduled_at,
                    taken_at = EXCLUDED.taken_at,
                    source = EXCLUDED.source,
                    metadata_json = EXCLUDED.metadata_json,
                    created_at = EXCLUDED.created_at
                """,
                (
                    event.id,
                    event.user_id,
                    event.regimen_id,
                    event.reminder_id,
                    event.status,
                    event.scheduled_at,
                    event.taken_at,
                    event.source,
                    self._jsonb(event.metadata),
                    event.created_at,
                ),
            )
        return event

    def list_medication_adherence_events(
        self,
        *,
        user_id: str,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[MedicationAdherenceEvent]:
        query = (
            "SELECT id, user_id, regimen_id, reminder_id, status, scheduled_at, taken_at, source, metadata_json, created_at "
            "FROM medication_adherence_events WHERE user_id = %s"
        )
        params: list[Any] = [user_id]
        if start_at is not None:
            query += " AND scheduled_at >= %s"
            params.append(start_at)
        if end_at is not None:
            query += " AND scheduled_at <= %s"
            params.append(end_at)
        query += " ORDER BY scheduled_at"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
        return [
            MedicationAdherenceEvent(
                id=row[0],
                user_id=row[1],
                regimen_id=row[2],
                reminder_id=row[3],
                status=row[4],
                scheduled_at=row[5],
                taken_at=row[6],
                source=row[7],
                metadata=cast(dict[str, object], _json_payload(row[8])),
                created_at=row[9],
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
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM reminder_notification_preferences
                WHERE user_id = %s AND scope_type = %s AND (
                    (scope_key IS NULL AND %s IS NULL) OR scope_key = %s
                )
                """,
                (user_id, scope_type, scope_key, scope_key),
            )
            for preference in preferences:
                cur.execute(
                    """
                    INSERT INTO reminder_notification_preferences
                    (id, user_id, scope_type, scope_key, channel, offset_minutes, enabled, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        preference.id,
                        preference.user_id,
                        preference.scope_type,
                        preference.scope_key,
                        preference.channel,
                        preference.offset_minutes,
                        preference.enabled,
                        preference.created_at,
                        preference.updated_at,
                    ),
                )
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
            "FROM reminder_notification_preferences WHERE user_id = %s"
        )
        params: list[Any] = [user_id]
        if scope_type is not None:
            query += " AND scope_type = %s"
            params.append(scope_type)
            if scope_key is None:
                query += " AND scope_key IS NULL"
            else:
                query += " AND scope_key = %s"
                params.append(scope_key)
        query += " ORDER BY scope_type, scope_key, offset_minutes, channel"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
        return [
            ReminderNotificationPreference(
                id=row[0],
                user_id=row[1],
                scope_type=row[2],
                scope_key=row[3],
                channel=row[4],
                offset_minutes=row[5],
                enabled=bool(row[6]),
                created_at=row[7],
                updated_at=row[8],
            )
            for row in rows
        ]

    def save_scheduled_notification(self, item: ScheduledReminderNotification) -> ScheduledReminderNotification:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scheduled_notifications
                (
                    id, reminder_id, user_id, channel, trigger_at, offset_minutes, preference_id,
                    status, attempt_count, next_attempt_at, queued_at, delivered_at, last_error,
                    payload_json, idempotency_key, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (
                    item.id,
                    item.reminder_id,
                    item.user_id,
                    item.channel,
                    item.trigger_at,
                    item.offset_minutes,
                    item.preference_id,
                    item.status,
                    item.attempt_count,
                    item.next_attempt_at,
                    item.queued_at,
                    item.delivered_at,
                    item.last_error,
                    self._jsonb(item.payload),
                    item.idempotency_key,
                    item.created_at,
                    item.updated_at,
                ),
            )
        existing = self.get_scheduled_notification(item.id)
        if existing is None:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM scheduled_notifications WHERE idempotency_key = %s",
                    (item.idempotency_key,),
                )
                row = cur.fetchone()
            if row is not None:
                existing = self.get_scheduled_notification(str(row[0]))
        if existing is None:
            raise RuntimeError(f"failed to persist scheduled notification {item.id}")
        return existing

    def get_scheduled_notification(self, notification_id: str) -> ScheduledReminderNotification | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, reminder_id, user_id, channel, trigger_at, offset_minutes, preference_id, status,
                       attempt_count, next_attempt_at, queued_at, delivered_at, last_error, payload_json,
                       idempotency_key, created_at, updated_at
                FROM scheduled_notifications
                WHERE id = %s
                """,
                (notification_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return ScheduledReminderNotification(
            id=row[0],
            reminder_id=row[1],
            user_id=row[2],
            channel=row[3],
            trigger_at=row[4],
            offset_minutes=row[5],
            preference_id=row[6],
            status=row[7],
            attempt_count=row[8],
            next_attempt_at=row[9],
            queued_at=row[10],
            delivered_at=row[11],
            last_error=row[12],
            payload=cast(dict[str, object], _json_payload(row[13])),
            idempotency_key=row[14],
            created_at=row[15],
            updated_at=row[16],
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
            query += " AND reminder_id = %s"
            params.append(reminder_id)
        if user_id is not None:
            query += " AND user_id = %s"
            params.append(user_id)
        query += " ORDER BY trigger_at, channel"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
        return [
            ScheduledReminderNotification(
                id=row[0],
                reminder_id=row[1],
                user_id=row[2],
                channel=row[3],
                trigger_at=row[4],
                offset_minutes=row[5],
                preference_id=row[6],
                status=row[7],
                attempt_count=row[8],
                next_attempt_at=row[9],
                queued_at=row[10],
                delivered_at=row[11],
                last_error=row[12],
                payload=cast(dict[str, object], _json_payload(row[13])),
                idempotency_key=row[14],
                created_at=row[15],
                updated_at=row[16],
            )
            for row in rows
        ]

    def lease_due_scheduled_notifications(self, *, now: datetime, limit: int = 100) -> list[ScheduledReminderNotification]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM scheduled_notifications
                WHERE status IN ('pending', 'retry_scheduled')
                  AND COALESCE(next_attempt_at, trigger_at) <= %s
                ORDER BY COALESCE(next_attempt_at, trigger_at), channel
                LIMIT %s
                """,
                (now, limit),
            )
            rows = cur.fetchall()
            leased: list[ScheduledReminderNotification] = []
            for row in rows:
                cur.execute(
                    """
                    UPDATE scheduled_notifications
                    SET status = 'queued', queued_at = %s, updated_at = %s, last_error = NULL
                    WHERE id = %s AND status IN ('pending', 'retry_scheduled')
                    """,
                    (now, now, str(row[0])),
                )
                if cur.rowcount != 1:
                    continue
                record = self.get_scheduled_notification(str(row[0]))
                if record is not None:
                    leased.append(record)
        return leased

    def set_scheduled_notification_trigger_at(self, notification_id: str, trigger_at: datetime) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE scheduled_notifications
                SET trigger_at = %s, next_attempt_at = %s, updated_at = %s
                WHERE id = %s
                """,
                (trigger_at, trigger_at, datetime.now(timezone.utc), notification_id),
            )

    def mark_scheduled_notification_processing(self, notification_id: str, attempt_count: int) -> None:
        now = datetime.now(timezone.utc)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE scheduled_notifications
                SET status = 'processing', attempt_count = %s, updated_at = %s
                WHERE id = %s
                """,
                (attempt_count, now, notification_id),
            )

    def mark_scheduled_notification_delivered(self, notification_id: str, attempt_count: int) -> None:
        now = datetime.now(timezone.utc)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE scheduled_notifications
                SET status = 'delivered', attempt_count = %s, delivered_at = %s, updated_at = %s, last_error = NULL
                WHERE id = %s
                """,
                (attempt_count, now, now, notification_id),
            )

    def reschedule_scheduled_notification(
        self,
        notification_id: str,
        *,
        attempt_count: int,
        next_attempt_at: datetime,
        error: str,
    ) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE scheduled_notifications
                SET status = 'retry_scheduled', attempt_count = %s, next_attempt_at = %s, last_error = %s, updated_at = %s
                WHERE id = %s
                """,
                (attempt_count, next_attempt_at, error, datetime.now(timezone.utc), notification_id),
            )

    def mark_scheduled_notification_dead_letter(
        self,
        notification_id: str,
        *,
        attempt_count: int,
        error: str,
    ) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE scheduled_notifications
                SET status = 'dead_letter', attempt_count = %s, last_error = %s, updated_at = %s
                WHERE id = %s
                """,
                (attempt_count, error, datetime.now(timezone.utc), notification_id),
            )

    def cancel_scheduled_notifications_for_reminder(self, reminder_id: str) -> int:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE scheduled_notifications
                SET status = 'cancelled', updated_at = %s
                WHERE reminder_id = %s AND status IN ('pending', 'queued', 'processing', 'retry_scheduled')
                """,
                (datetime.now(timezone.utc), reminder_id),
            )
            return int(cur.rowcount)

    def append_notification_log(self, entry: ReminderNotificationLogEntry) -> ReminderNotificationLogEntry:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO notification_logs
                (id, scheduled_notification_id, reminder_id, user_id, channel, attempt_number, event_type, error_message, metadata_json, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    self._jsonb(entry.metadata),
                    entry.created_at,
                ),
            )
        return entry

    def replace_reminder_notification_endpoints(
        self,
        *,
        user_id: str,
        endpoints: list[ReminderNotificationEndpoint],
    ) -> list[ReminderNotificationEndpoint]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM reminder_notification_endpoints WHERE user_id = %s", (user_id,))
            for endpoint in endpoints:
                cur.execute(
                    """
                    INSERT INTO reminder_notification_endpoints
                    (id, user_id, channel, destination, verified, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        endpoint.id,
                        endpoint.user_id,
                        endpoint.channel,
                        endpoint.destination,
                        endpoint.verified,
                        endpoint.created_at,
                        endpoint.updated_at,
                    ),
                )
        return self.list_reminder_notification_endpoints(user_id=user_id)

    def list_reminder_notification_endpoints(self, *, user_id: str) -> list[ReminderNotificationEndpoint]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, channel, destination, verified, created_at, updated_at
                FROM reminder_notification_endpoints
                WHERE user_id = %s
                ORDER BY channel
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        return [
            ReminderNotificationEndpoint(
                id=row[0],
                user_id=row[1],
                channel=row[2],
                destination=row[3],
                verified=bool(row[4]),
                created_at=row[5],
                updated_at=row[6],
            )
            for row in rows
        ]

    def get_reminder_notification_endpoint(self, *, user_id: str, channel: str) -> ReminderNotificationEndpoint | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, channel, destination, verified, created_at, updated_at
                FROM reminder_notification_endpoints
                WHERE user_id = %s AND channel = %s
                """,
                (user_id, channel),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return ReminderNotificationEndpoint(
            id=row[0],
            user_id=row[1],
            channel=row[2],
            destination=row[3],
            verified=bool(row[4]),
            created_at=row[5],
            updated_at=row[6],
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
            query += " AND reminder_id = %s"
            params.append(reminder_id)
        if scheduled_notification_id is not None:
            query += " AND scheduled_notification_id = %s"
            params.append(scheduled_notification_id)
        query += " ORDER BY created_at"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
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
                metadata=cast(dict[str, object], _json_payload(row[8])),
                created_at=row[9],
            )
            for row in rows
        ]

    def save_meal_record(self, record: MealRecognitionRecord) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO meal_records
                (id, user_id, captured_at, source, meal_state_json, analysis_version, multi_item_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    captured_at = EXCLUDED.captured_at,
                    source = EXCLUDED.source,
                    meal_state_json = EXCLUDED.meal_state_json,
                    analysis_version = EXCLUDED.analysis_version,
                    multi_item_count = EXCLUDED.multi_item_count
                """,
                (
                    record.id,
                    record.user_id,
                    record.captured_at,
                    record.source,
                    self._jsonb(record.meal_state.model_dump(mode="json")),
                    record.analysis_version,
                    record.multi_item_count,
                ),
            )
        logger.info(
            "save_meal_record id=%s user_id=%s dish=%s multi_item_count=%s",
            record.id,
            record.user_id,
            record.meal_state.dish_name,
            record.multi_item_count,
        )

    def list_meal_records(self, user_id: str) -> list[MealRecognitionRecord]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, captured_at, source, meal_state_json, analysis_version, multi_item_count
                FROM meal_records
                WHERE user_id = %s
                ORDER BY captured_at
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        out = [
            MealRecognitionRecord(
                id=row[0],
                user_id=row[1],
                captured_at=row[2],
                source=row[3],
                meal_state=MealState.model_validate(_json_payload(row[4])),
                analysis_version=row[5],
                multi_item_count=row[6],
            )
            for row in rows
        ]
        logger.debug("list_meal_records user_id=%s count=%s", user_id, len(out))
        return out

    def get_meal_record(self, user_id: str, meal_id: str) -> MealRecognitionRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, captured_at, source, meal_state_json, analysis_version, multi_item_count
                FROM meal_records
                WHERE user_id = %s AND id = %s
                """,
                (user_id, meal_id),
            )
            row = cur.fetchone()
        if row is None:
            logger.debug("get_meal_record_miss user_id=%s meal_id=%s", user_id, meal_id)
            return None
        return MealRecognitionRecord(
            id=row[0],
            user_id=row[1],
            captured_at=row[2],
            source=row[3],
            meal_state=MealState.model_validate(_json_payload(row[4])),
            analysis_version=row[5],
            multi_item_count=row[6],
        )

    def save_biomarker_readings(self, user_id: str, readings: list[BiomarkerReading]) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            for reading in readings:
                cur.execute(
                    """
                    INSERT INTO biomarker_readings
                    (user_id, name, value, unit, reference_range, measured_at, source_doc_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        reading.name,
                        reading.value,
                        reading.unit,
                        reading.reference_range,
                        reading.measured_at,
                        reading.source_doc_id,
                    ),
                )
        logger.info("save_biomarker_readings user_id=%s count=%s", user_id, len(readings))

    def list_biomarker_readings(self, user_id: str) -> list[BiomarkerReading]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT name, value, unit, reference_range, measured_at, source_doc_id
                FROM biomarker_readings
                WHERE user_id = %s
                ORDER BY measured_at
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        readings = [
            BiomarkerReading(
                name=row[0],
                value=row[1],
                unit=row[2],
                reference_range=row[3],
                measured_at=row[4],
                source_doc_id=row[5],
            )
            for row in rows
        ]
        logger.debug("list_biomarker_readings user_id=%s count=%s", user_id, len(readings))
        return readings

    def save_symptom_checkin(self, checkin: SymptomCheckIn) -> SymptomCheckIn:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO symptom_checkins
                (id, user_id, recorded_at, severity, symptom_codes_json, free_text, context_json, safety_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    recorded_at = EXCLUDED.recorded_at,
                    severity = EXCLUDED.severity,
                    symptom_codes_json = EXCLUDED.symptom_codes_json,
                    free_text = EXCLUDED.free_text,
                    context_json = EXCLUDED.context_json,
                    safety_json = EXCLUDED.safety_json
                """,
                (
                    checkin.id,
                    checkin.user_id,
                    checkin.recorded_at,
                    checkin.severity,
                    self._jsonb(checkin.symptom_codes),
                    checkin.free_text,
                    self._jsonb(checkin.context),
                    self._jsonb(checkin.safety.model_dump(mode="json")),
                ),
            )
        return checkin

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
            "FROM symptom_checkins WHERE user_id = %s"
        )
        params: list[Any] = [user_id]
        if start_at is not None:
            query += " AND recorded_at >= %s"
            params.append(start_at)
        if end_at is not None:
            query += " AND recorded_at <= %s"
            params.append(end_at)
        query += " ORDER BY recorded_at DESC LIMIT %s"
        params.append(max(1, min(limit, 1000)))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
        return [
            SymptomCheckIn(
                id=row[0],
                user_id=row[1],
                recorded_at=row[2],
                severity=int(row[3]),
                symptom_codes=cast(list[str], _json_payload(row[4])),
                free_text=row[5],
                context=cast(dict[str, object], _json_payload(row[6])),
                safety=SymptomSafety.model_validate(_json_payload(row[7])),
            )
            for row in rows
        ]

    def save_clinical_card(self, card: ClinicalCardRecord) -> ClinicalCardRecord:
        payload = card.model_dump(mode="json")
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO clinical_cards
                (id, user_id, created_at, start_date, end_date, format, payload_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    created_at = EXCLUDED.created_at,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    format = EXCLUDED.format,
                    payload_json = EXCLUDED.payload_json
                """,
                (
                    card.id,
                    card.user_id,
                    card.created_at,
                    card.start_date,
                    card.end_date,
                    card.format,
                    self._jsonb(payload),
                ),
            )
        return card

    def list_clinical_cards(self, *, user_id: str, limit: int = 50) -> list[ClinicalCardRecord]:
        bounded = max(1, min(limit, 200))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT payload_json
                FROM clinical_cards
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, bounded),
            )
            rows = cur.fetchall()
        return [ClinicalCardRecord.model_validate(_json_payload(row[0])) for row in rows]

    def get_clinical_card(self, *, user_id: str, card_id: str) -> ClinicalCardRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT payload_json FROM clinical_cards WHERE user_id = %s AND id = %s",
                (user_id, card_id),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return ClinicalCardRecord.model_validate(_json_payload(row[0]))

    def save_tool_role_policy(self, record: ToolRolePolicyRecord) -> ToolRolePolicyRecord:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tool_role_policies
                (id, role, agent_id, tool_name, effect, conditions_json, priority, enabled, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    role = EXCLUDED.role,
                    agent_id = EXCLUDED.agent_id,
                    tool_name = EXCLUDED.tool_name,
                    effect = EXCLUDED.effect,
                    conditions_json = EXCLUDED.conditions_json,
                    priority = EXCLUDED.priority,
                    enabled = EXCLUDED.enabled,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    record.id,
                    record.role,
                    record.agent_id,
                    record.tool_name,
                    record.effect,
                    self._jsonb(record.conditions),
                    record.priority,
                    record.enabled,
                    record.created_at,
                    record.updated_at,
                ),
            )
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
            query += " AND role = %s"
            params.append(role)
        if agent_id is not None:
            query += " AND agent_id = %s"
            params.append(agent_id)
        if tool_name is not None:
            query += " AND tool_name = %s"
            params.append(tool_name)
        if enabled_only:
            query += " AND enabled = TRUE"
        query += " ORDER BY priority DESC, updated_at DESC, id"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
        return [
            ToolRolePolicyRecord(
                id=row[0],
                role=row[1],
                agent_id=row[2],
                tool_name=row[3],
                effect=row[4],
                conditions=cast(dict[str, object], _json_payload(row[5])),
                priority=int(row[6]),
                enabled=bool(row[7]),
                created_at=row[8],
                updated_at=row[9],
            )
            for row in rows
        ]

    def get_tool_role_policy(self, policy_id: str) -> ToolRolePolicyRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, role, agent_id, tool_name, effect, conditions_json, priority, enabled, created_at, updated_at
                FROM tool_role_policies WHERE id = %s
                """,
                (policy_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return ToolRolePolicyRecord(
            id=row[0],
            role=row[1],
            agent_id=row[2],
            tool_name=row[3],
            effect=row[4],
            conditions=cast(dict[str, object], _json_payload(row[5])),
            priority=int(row[6]),
            enabled=bool(row[7]),
            created_at=row[8],
            updated_at=row[9],
        )

    def save_workflow_contract_snapshot(
        self,
        snapshot: WorkflowContractSnapshotRecord,
    ) -> WorkflowContractSnapshotRecord:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workflow_contract_snapshots
                (id, version, contract_hash, source, workflows_json, agents_json, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    version = EXCLUDED.version,
                    contract_hash = EXCLUDED.contract_hash,
                    source = EXCLUDED.source,
                    workflows_json = EXCLUDED.workflows_json,
                    agents_json = EXCLUDED.agents_json,
                    created_by = EXCLUDED.created_by,
                    created_at = EXCLUDED.created_at
                """,
                (
                    snapshot.id,
                    snapshot.version,
                    snapshot.contract_hash,
                    snapshot.source,
                    self._jsonb([item.model_dump(mode="json") for item in snapshot.workflows]),
                    self._jsonb([item.model_dump(mode="json") for item in snapshot.agents]),
                    snapshot.created_by,
                    snapshot.created_at,
                ),
            )
        return snapshot

    def list_workflow_contract_snapshots(self, *, limit: int = 50) -> list[WorkflowContractSnapshotRecord]:
        bounded = max(1, min(int(limit), 200))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, version, contract_hash, source, workflows_json, agents_json, created_by, created_at
                FROM workflow_contract_snapshots
                ORDER BY version DESC
                LIMIT %s
                """,
                (bounded,),
            )
            rows = cur.fetchall()
        return [
            WorkflowContractSnapshotRecord(
                id=row[0],
                version=int(row[1]),
                contract_hash=row[2],
                source=row[3],
                workflows=[WorkflowRuntimeContract.model_validate(item) for item in cast(list[dict[str, object]], _json_payload(row[4]))],
                agents=[AgentContract.model_validate(item) for item in cast(list[dict[str, object]], _json_payload(row[5]))],
                created_by=row[6],
                created_at=row[7],
            )
            for row in rows
        ]

    def get_workflow_contract_snapshot(self, *, version: int) -> WorkflowContractSnapshotRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, version, contract_hash, source, workflows_json, agents_json, created_by, created_at
                FROM workflow_contract_snapshots
                WHERE version = %s
                """,
                (version,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return WorkflowContractSnapshotRecord(
            id=row[0],
            version=int(row[1]),
            contract_hash=row[2],
            source=row[3],
            workflows=[WorkflowRuntimeContract.model_validate(item) for item in cast(list[dict[str, object]], _json_payload(row[4]))],
            agents=[AgentContract.model_validate(item) for item in cast(list[dict[str, object]], _json_payload(row[5]))],
            created_by=row[6],
            created_at=row[7],
        )

    def save_recommendation(self, user_id: str, payload: dict[str, Any]) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO recommendation_records(user_id, created_at, payload_json)
                VALUES (%s, %s, %s)
                """,
                (user_id, datetime.now(timezone.utc), self._jsonb(payload)),
            )
        logger.info("save_recommendation user_id=%s payload_keys=%s", user_id, sorted(payload.keys()))

    def get_health_profile(self, user_id: str) -> HealthProfileRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT payload_json FROM health_profiles WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
        if row is None:
            logger.debug("get_health_profile_miss user_id=%s", user_id)
            return None
        logger.debug("get_health_profile_hit user_id=%s", user_id)
        return _model_from_payload(HealthProfileRecord, row[0])

    def save_health_profile(self, profile: HealthProfileRecord) -> HealthProfileRecord:
        payload = profile.model_dump(mode="json")
        updated_at = _coerce_datetime(payload.get("updated_at")) or datetime.now(timezone.utc)
        payload["updated_at"] = updated_at.isoformat()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO health_profiles (user_id, updated_at, payload_json)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    updated_at = EXCLUDED.updated_at,
                    payload_json = EXCLUDED.payload_json
                """,
                (profile.user_id, updated_at, self._jsonb(payload)),
            )
        logger.info("save_health_profile user_id=%s goals=%s", profile.user_id, len(profile.nutrition_goals))
        return HealthProfileRecord.model_validate(payload)

    def get_health_profile_onboarding_state(self, user_id: str) -> HealthProfileOnboardingState | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT payload_json FROM health_profile_onboarding_states WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
        if row is None:
            logger.debug("get_health_profile_onboarding_state_miss user_id=%s", user_id)
            return None
        logger.debug("get_health_profile_onboarding_state_hit user_id=%s", user_id)
        return _model_from_payload(HealthProfileOnboardingState, row[0])

    def save_health_profile_onboarding_state(
        self,
        state: HealthProfileOnboardingState,
    ) -> HealthProfileOnboardingState:
        payload = state.model_dump(mode="json")
        updated_at = _coerce_datetime(payload.get("updated_at")) or datetime.now(timezone.utc)
        payload["updated_at"] = updated_at.isoformat()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO health_profile_onboarding_states (user_id, updated_at, payload_json)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    updated_at = EXCLUDED.updated_at,
                    payload_json = EXCLUDED.payload_json
                """,
                (state.user_id, updated_at, self._jsonb(payload)),
            )
        logger.info(
            "save_health_profile_onboarding_state user_id=%s current_step=%s complete=%s",
            state.user_id,
            state.current_step,
            state.is_complete,
        )
        return HealthProfileOnboardingState.model_validate(payload)

    def get_mobility_reminder_settings(self, user_id: str) -> MobilityReminderSettings | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT payload_json FROM mobility_reminder_settings WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
        if row is None:
            return None
        return _model_from_payload(MobilityReminderSettings, row[0])

    def save_mobility_reminder_settings(self, settings: MobilityReminderSettings) -> MobilityReminderSettings:
        payload = settings.model_dump(mode="json")
        updated_at = _coerce_datetime(payload.get("updated_at")) or datetime.now(timezone.utc)
        payload["updated_at"] = updated_at.isoformat()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO mobility_reminder_settings (user_id, updated_at, payload_json)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    updated_at = EXCLUDED.updated_at,
                    payload_json = EXCLUDED.payload_json
                """,
                (settings.user_id, updated_at, self._jsonb(payload)),
            )
        return MobilityReminderSettings.model_validate(payload)

    def list_meal_catalog_items(self, *, locale: str, slot: str | None = None, limit: int = 100) -> list[MealCatalogItem]:
        bounded = max(1, min(int(limit), 200))
        query = "SELECT payload_json FROM meal_catalog WHERE locale = %s AND active = TRUE"
        params: list[Any] = [locale]
        if slot is not None:
            query += " AND slot = %s"
            params.append(slot)
        query += " ORDER BY meal_id LIMIT %s"
        params.append(bounded)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
        return [_model_from_payload(MealCatalogItem, row[0]) for row in rows]

    def get_meal_catalog_item(self, meal_id: str) -> MealCatalogItem | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT payload_json FROM meal_catalog WHERE meal_id = %s", (meal_id,))
            row = cur.fetchone()
        if row is None:
            return None
        return _model_from_payload(MealCatalogItem, row[0])

    def save_recommendation_interaction(self, interaction: RecommendationInteraction) -> RecommendationInteraction:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO recommendation_interactions
                (interaction_id, user_id, recommendation_id, candidate_id, event_type, slot, source_meal_id, selected_meal_id, created_at, metadata_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (interaction_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    recommendation_id = EXCLUDED.recommendation_id,
                    candidate_id = EXCLUDED.candidate_id,
                    event_type = EXCLUDED.event_type,
                    slot = EXCLUDED.slot,
                    source_meal_id = EXCLUDED.source_meal_id,
                    selected_meal_id = EXCLUDED.selected_meal_id,
                    created_at = EXCLUDED.created_at,
                    metadata_json = EXCLUDED.metadata_json
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
                    interaction.created_at,
                    self._jsonb(interaction.metadata),
                ),
            )
        logger.info(
            "save_recommendation_interaction user_id=%s candidate_id=%s event_type=%s",
            interaction.user_id,
            interaction.candidate_id,
            interaction.event_type,
        )
        return interaction

    def list_recommendation_interactions(self, user_id: str, *, limit: int = 200) -> list[RecommendationInteraction]:
        bounded = max(1, min(int(limit), 1000))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT interaction_id, user_id, recommendation_id, candidate_id, event_type, slot, source_meal_id, selected_meal_id, created_at, metadata_json
                FROM recommendation_interactions
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, bounded),
            )
            rows = cur.fetchall()
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
                created_at=row[8],
                metadata=cast(dict[str, object], _json_payload(row[9])),
            )
            for row in rows
        ]

    def get_preference_snapshot(self, user_id: str) -> PreferenceSnapshot | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT payload_json FROM preference_snapshots WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
        if row is None:
            logger.debug("get_preference_snapshot_miss user_id=%s", user_id)
            return None
        return _model_from_payload(PreferenceSnapshot, row[0])

    def save_preference_snapshot(self, snapshot: PreferenceSnapshot) -> PreferenceSnapshot:
        payload = snapshot.model_dump(mode="json")
        updated_at = _coerce_datetime(payload.get("updated_at")) or datetime.now(timezone.utc)
        payload["updated_at"] = updated_at.isoformat()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO preference_snapshots (user_id, updated_at, payload_json)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    updated_at = EXCLUDED.updated_at,
                    payload_json = EXCLUDED.payload_json
                """,
                (snapshot.user_id, updated_at, self._jsonb(payload)),
            )
        logger.info(
            "save_preference_snapshot user_id=%s interactions=%s",
            snapshot.user_id,
            snapshot.interaction_count,
        )
        return PreferenceSnapshot.model_validate(payload)

    def save_suggestion_record(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        suggestion_id = str(payload.get("suggestion_id", ""))
        created_at = _coerce_datetime(payload.get("created_at"))
        if not suggestion_id or created_at is None:
            raise ValueError("suggestion payload requires suggestion_id and created_at")
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO suggestion_records(suggestion_id, user_id, created_at, payload_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (suggestion_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    created_at = EXCLUDED.created_at,
                    payload_json = EXCLUDED.payload_json
                """,
                (suggestion_id, user_id, created_at, self._jsonb(payload)),
            )
        logger.info("save_suggestion_record user_id=%s suggestion_id=%s", user_id, suggestion_id)
        return payload

    def list_suggestion_records(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(limit, 100))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT payload_json
                FROM suggestion_records
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, bounded_limit),
            )
            rows = cur.fetchall()
        items = [cast(dict[str, Any], _json_payload(row[0])) for row in rows]
        logger.debug("list_suggestion_records user_id=%s count=%s", user_id, len(items))
        return items

    def get_suggestion_record(self, user_id: str, suggestion_id: str) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT payload_json
                FROM suggestion_records
                WHERE user_id = %s AND suggestion_id = %s
                """,
                (user_id, suggestion_id),
            )
            row = cur.fetchone()
        if row is None:
            logger.debug("get_suggestion_record_miss user_id=%s suggestion_id=%s", user_id, suggestion_id)
            return None
        item = cast(dict[str, Any], _json_payload(row[0]))
        logger.debug("get_suggestion_record_hit user_id=%s suggestion_id=%s", user_id, suggestion_id)
        return item

    def enqueue_alert(self, message: AlertMessage) -> list[OutboxRecord]:
        created: list[OutboxRecord] = []
        now = datetime.now(timezone.utc)
        with self._connect() as conn, conn.cursor() as cur:
            for sink in message.destinations:
                idempotency_key = f"{message.alert_id}:{sink}"
                cur.execute(
                    """
                    INSERT INTO alert_outbox
                    (
                        alert_id, sink, type, severity, payload_json, correlation_id, created_at,
                        state, attempt_count, next_attempt_at, last_error, lease_owner, lease_until, idempotency_key
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        message.alert_id,
                        sink,
                        message.type,
                        message.severity,
                        self._jsonb(message.payload),
                        message.correlation_id,
                        message.created_at,
                        "pending",
                        0,
                        now,
                        None,
                        None,
                        None,
                        idempotency_key,
                    ),
                )
                if cur.rowcount != 1:
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
              AND next_attempt_at <= %s
              AND (lease_until IS NULL OR lease_until <= %s)
        """
        params: list[Any] = [now, now]
        if alert_id is not None:
            query += " AND alert_id = %s"
            params.append(alert_id)
        query += " ORDER BY next_attempt_at LIMIT %s"
        params.append(limit)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            leased: list[OutboxRecord] = []
            for row in rows:
                cur.execute(
                    """
                    UPDATE alert_outbox
                    SET state = 'processing', lease_owner = %s, lease_until = %s
                    WHERE alert_id = %s AND sink = %s
                      AND state IN ('pending', 'processing')
                      AND next_attempt_at <= %s
                      AND (lease_until IS NULL OR lease_until <= %s)
                    """,
                    (lease_owner, lease_until, row[0], row[1], now, now),
                )
                if cur.rowcount != 1:
                    continue
                leased.append(
                    OutboxRecord(
                        alert_id=row[0],
                        sink=row[1],
                        type=row[2],
                        severity=row[3],
                        payload=cast(dict[str, str], _json_payload(row[4])),
                        correlation_id=row[5],
                        created_at=row[6],
                        state="processing",
                        attempt_count=row[8],
                        next_attempt_at=row[9],
                        last_error=row[10],
                        lease_owner=lease_owner,
                        lease_until=lease_until,
                        idempotency_key=row[13],
                    )
                )
        return leased

    def mark_alert_delivered(self, alert_id: str, sink: str, attempt_count: int | None = None) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            if attempt_count is None:
                cur.execute(
                    """
                    UPDATE alert_outbox
                    SET state = 'delivered', lease_owner = NULL, lease_until = NULL, last_error = NULL
                    WHERE alert_id = %s AND sink = %s
                    """,
                    (alert_id, sink),
                )
            else:
                cur.execute(
                    """
                    UPDATE alert_outbox
                    SET state = 'delivered', attempt_count = %s, lease_owner = NULL, lease_until = NULL, last_error = NULL
                    WHERE alert_id = %s AND sink = %s
                    """,
                    (attempt_count, alert_id, sink),
                )

    def reschedule_alert(
        self,
        alert_id: str,
        sink: str,
        next_attempt_at: datetime,
        attempt_count: int,
        error: str,
    ) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE alert_outbox
                SET state = 'pending', attempt_count = %s, next_attempt_at = %s, last_error = %s, lease_owner = NULL, lease_until = NULL
                WHERE alert_id = %s AND sink = %s
                """,
                (attempt_count, next_attempt_at, error, alert_id, sink),
            )

    def mark_alert_dead_letter(
        self,
        alert_id: str,
        sink: str,
        error: str,
        attempt_count: int | None = None,
    ) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            if attempt_count is None:
                cur.execute(
                    """
                    UPDATE alert_outbox
                    SET state = 'dead_letter', last_error = %s, lease_owner = NULL, lease_until = NULL
                    WHERE alert_id = %s AND sink = %s
                    """,
                    (error, alert_id, sink),
                )
            else:
                cur.execute(
                    """
                    UPDATE alert_outbox
                    SET state = 'dead_letter', attempt_count = %s, last_error = %s, lease_owner = NULL, lease_until = NULL
                    WHERE alert_id = %s AND sink = %s
                    """,
                    (attempt_count, error, alert_id, sink),
                )

    def list_alert_records(self, alert_id: str | None = None) -> list[OutboxRecord]:
        query = (
            "SELECT alert_id, sink, type, severity, payload_json, correlation_id, created_at, "
            "state, attempt_count, next_attempt_at, last_error, lease_owner, lease_until, idempotency_key "
            "FROM alert_outbox"
        )
        params: tuple[Any, ...] = ()
        if alert_id is not None:
            query += " WHERE alert_id = %s"
            params = (alert_id,)
        query += " ORDER BY next_attempt_at"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return [
            OutboxRecord(
                alert_id=row[0],
                sink=row[1],
                type=row[2],
                severity=row[3],
                payload=cast(dict[str, str], _json_payload(row[4])),
                correlation_id=row[5],
                created_at=row[6],
                state=row[7],
                attempt_count=row[8],
                next_attempt_at=row[9],
                last_error=row[10],
                lease_owner=row[11],
                lease_until=row[12],
                idempotency_key=row[13],
            )
            for row in rows
        ]

    def close(self) -> None:
        return None
