"""
Persist reminder scheduling data in SQLite.

This module implements SQLite storage for reminders, scheduled notifications,
and endpoints.
"""

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

from care_pilot.config.app import get_settings
from care_pilot.features.reminders.domain.models import (
    MobilityReminderSettings,
    ReminderActionRecord,
    ReminderDefinition,
    ReminderEvent,
    ReminderNotificationEndpoint,
    ReminderNotificationLogEntry,
    ReminderNotificationPreference,
    ReminderOccurrence,
    ReminderScheduleRule,
    ScheduledReminderNotification,
)
from care_pilot.platform.observability.setup import get_logger

logger = get_logger(__name__)


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        settings = get_settings()
        parsed = parsed.replace(tzinfo=ZoneInfo(settings.app.timezone)).astimezone(UTC)
    return parsed


class SQLiteReminderRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def save_reminder_definition(self, definition: ReminderDefinition) -> ReminderDefinition:
        payload = definition.model_dump(mode="json")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO reminder_definitions (
                    id, user_id, regimen_id, reminder_type, source, title, body,
                    medication_name, dosage_text, route, instructions_text, special_notes,
                    treatment_duration, channels_json, timezone, schedule_json, active,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    definition.id,
                    definition.user_id,
                    definition.regimen_id,
                    definition.reminder_type,
                    definition.source,
                    definition.title,
                    definition.body,
                    definition.medication_name,
                    definition.dosage_text,
                    definition.route,
                    definition.instructions_text,
                    definition.special_notes,
                    definition.treatment_duration,
                    json.dumps(payload["channels"]),
                    definition.timezone,
                    json.dumps(payload["schedule"]),
                    int(definition.active),
                    definition.created_at.isoformat(),
                    definition.updated_at.isoformat(),
                ),
            )
            conn.commit()
        saved = self.get_reminder_definition(definition.id)
        if saved is None:
            raise RuntimeError(f"failed to persist reminder definition {definition.id}")
        return saved

    def get_reminder_definition(self, reminder_definition_id: str) -> ReminderDefinition | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, user_id, regimen_id, reminder_type, source, title, body,
                       medication_name, dosage_text, route, instructions_text, special_notes,
                       treatment_duration, channels_json, timezone, schedule_json, active,
                       created_at, updated_at
                FROM reminder_definitions
                WHERE id = ?
                """,
                (reminder_definition_id,),
            ).fetchone()
        if row is None:
            return None
        return ReminderDefinition(
            id=row[0],
            user_id=row[1],
            regimen_id=row[2],
            reminder_type=row[3],
            source=row[4],
            title=row[5],
            body=row[6],
            medication_name=row[7],
            dosage_text=row[8],
            route=row[9],
            instructions_text=row[10],
            special_notes=row[11],
            treatment_duration=row[12],
            channels=json.loads(cast(str, row[13])),
            timezone=row[14],
            schedule=ReminderScheduleRule.model_validate(json.loads(cast(str, row[15]))),
            active=bool(row[16]),
            created_at=cast(datetime, _parse_datetime(row[17])),
            updated_at=cast(datetime, _parse_datetime(row[18])),
        )

    def list_reminder_definitions(
        self, user_id: str, *, active_only: bool = False
    ) -> list[ReminderDefinition]:
        query = (
            "SELECT id, user_id, regimen_id, reminder_type, source, title, body, medication_name, dosage_text, "
            "route, instructions_text, special_notes, treatment_duration, channels_json, timezone, schedule_json, "
            "active, created_at, updated_at FROM reminder_definitions WHERE user_id = ?"
        )
        params: list[Any] = [user_id]
        if active_only:
            query += " AND active = 1"
        query += " ORDER BY updated_at DESC, title"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            ReminderDefinition(
                id=row[0],
                user_id=row[1],
                regimen_id=row[2],
                reminder_type=row[3],
                source=row[4],
                title=row[5],
                body=row[6],
                medication_name=row[7],
                dosage_text=row[8],
                route=row[9],
                instructions_text=row[10],
                special_notes=row[11],
                treatment_duration=row[12],
                channels=json.loads(cast(str, row[13])),
                timezone=row[14],
                schedule=ReminderScheduleRule.model_validate(json.loads(cast(str, row[15]))),
                active=bool(row[16]),
                created_at=cast(datetime, _parse_datetime(row[17])),
                updated_at=cast(datetime, _parse_datetime(row[18])),
            )
            for row in rows
        ]

    def save_reminder_occurrence(self, occurrence: ReminderOccurrence) -> ReminderOccurrence:
        payload = occurrence.model_dump(mode="json")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO reminder_occurrences (
                    id, reminder_definition_id, user_id, scheduled_for, trigger_at, status, action,
                    action_outcome, acted_at, grace_window_minutes, retry_count, last_delivery_status,
                    metadata_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    occurrence.id,
                    occurrence.reminder_definition_id,
                    occurrence.user_id,
                    occurrence.scheduled_for.isoformat(),
                    occurrence.trigger_at.isoformat(),
                    occurrence.status,
                    occurrence.action,
                    occurrence.action_outcome,
                    (occurrence.acted_at.isoformat() if occurrence.acted_at else None),
                    occurrence.grace_window_minutes,
                    occurrence.retry_count,
                    occurrence.last_delivery_status,
                    json.dumps(payload["metadata"]),
                    occurrence.created_at.isoformat(),
                    occurrence.updated_at.isoformat(),
                ),
            )
            conn.commit()
        saved = self.get_reminder_occurrence(occurrence.id)
        if saved is None:
            raise RuntimeError(f"failed to persist reminder occurrence {occurrence.id}")
        return saved

    def get_reminder_occurrence(self, occurrence_id: str) -> ReminderOccurrence | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, reminder_definition_id, user_id, scheduled_for, trigger_at, status, action,
                       action_outcome, acted_at, grace_window_minutes, retry_count, last_delivery_status,
                       metadata_json, created_at, updated_at
                FROM reminder_occurrences
                WHERE id = ?
                """,
                (occurrence_id,),
            ).fetchone()
        if row is None:
            return None
        return ReminderOccurrence(
            id=row[0],
            reminder_definition_id=row[1],
            user_id=row[2],
            scheduled_for=cast(datetime, _parse_datetime(row[3])),
            trigger_at=cast(datetime, _parse_datetime(row[4])),
            status=row[5],
            action=row[6],
            action_outcome=row[7],
            acted_at=_parse_datetime(row[8]),
            grace_window_minutes=row[9],
            retry_count=row[10],
            last_delivery_status=row[11],
            metadata=json.loads(cast(str, row[12])),
            created_at=cast(datetime, _parse_datetime(row[13])),
            updated_at=cast(datetime, _parse_datetime(row[14])),
        )

    def list_reminder_occurrences(
        self,
        *,
        user_id: str,
        reminder_definition_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[ReminderOccurrence]:
        query = (
            "SELECT id, reminder_definition_id, user_id, scheduled_for, trigger_at, status, action, action_outcome, "
            "acted_at, grace_window_minutes, retry_count, last_delivery_status, metadata_json, created_at, updated_at "
            "FROM reminder_occurrences WHERE user_id = ?"
        )
        params: list[Any] = [user_id]
        if reminder_definition_id is not None:
            query += " AND reminder_definition_id = ?"
            params.append(reminder_definition_id)
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY trigger_at LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            ReminderOccurrence(
                id=row[0],
                reminder_definition_id=row[1],
                user_id=row[2],
                scheduled_for=cast(datetime, _parse_datetime(row[3])),
                trigger_at=cast(datetime, _parse_datetime(row[4])),
                status=row[5],
                action=row[6],
                action_outcome=row[7],
                acted_at=_parse_datetime(row[8]),
                grace_window_minutes=row[9],
                retry_count=row[10],
                last_delivery_status=row[11],
                metadata=json.loads(cast(str, row[12])),
                created_at=cast(datetime, _parse_datetime(row[13])),
                updated_at=cast(datetime, _parse_datetime(row[14])),
            )
            for row in rows
        ]

    def append_reminder_action(self, action: ReminderActionRecord) -> ReminderActionRecord:
        payload = action.model_dump(mode="json")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO reminder_actions
                (id, occurrence_id, reminder_definition_id, user_id, action, acted_at, snooze_minutes, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.id,
                    action.occurrence_id,
                    action.reminder_definition_id,
                    action.user_id,
                    action.action,
                    action.acted_at.isoformat(),
                    action.snooze_minutes,
                    json.dumps(payload["metadata"]),
                ),
            )
            conn.commit()
        return action

    def list_reminder_actions(
        self,
        *,
        occurrence_id: str | None = None,
        reminder_definition_id: str | None = None,
        limit: int = 200,
    ) -> list[ReminderActionRecord]:
        query = (
            "SELECT id, occurrence_id, reminder_definition_id, user_id, action, acted_at, snooze_minutes, metadata_json "
            "FROM reminder_actions WHERE 1=1"
        )
        params: list[Any] = []
        if occurrence_id is not None:
            query += " AND occurrence_id = ?"
            params.append(occurrence_id)
        if reminder_definition_id is not None:
            query += " AND reminder_definition_id = ?"
            params.append(reminder_definition_id)
        query += " ORDER BY acted_at LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            ReminderActionRecord(
                id=row[0],
                occurrence_id=row[1],
                reminder_definition_id=row[2],
                user_id=row[3],
                action=row[4],
                acted_at=cast(datetime, _parse_datetime(row[5])),
                snooze_minutes=row[6],
                metadata=json.loads(cast(str, row[7])),
            )
            for row in rows
        ]

    def update_reminder_occurrence_status(
        self,
        *,
        occurrence_id: str,
        status: str,
        acted_at: datetime | None = None,
        action: str | None = None,
        action_outcome: str | None = None,
        trigger_at: datetime | None = None,
    ) -> ReminderOccurrence | None:
        now = datetime.now(UTC)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE reminder_occurrences
                SET status = ?, acted_at = COALESCE(?, acted_at), action = COALESCE(?, action),
                    action_outcome = COALESCE(?, action_outcome), trigger_at = COALESCE(?, trigger_at), updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    acted_at.isoformat() if acted_at else None,
                    action,
                    action_outcome,
                    trigger_at.isoformat() if trigger_at else None,
                    now.isoformat(),
                    occurrence_id,
                ),
            )
            conn.commit()
        return self.get_reminder_occurrence(occurrence_id)

    def save_reminder_event(self, event: ReminderEvent) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO reminder_events
                (id, user_id, reminder_definition_id, occurrence_id, regimen_id, reminder_type, title, body, medication_name, scheduled_at, slot, dosage_text, status, meal_confirmation, sent_at, ack_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.user_id,
                    event.reminder_definition_id,
                    event.occurrence_id,
                    event.regimen_id,
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
                SELECT id, user_id, reminder_definition_id, occurrence_id, regimen_id, reminder_type, title, body, medication_name, scheduled_at, slot, dosage_text, status, meal_confirmation, sent_at, ack_at
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
            reminder_definition_id=row[2],
            occurrence_id=row[3],
            regimen_id=row[4],
            reminder_type=row[5],
            title=row[6],
            body=row[7],
            medication_name=row[8],
            scheduled_at=cast(datetime, _parse_datetime(row[9])),
            slot=row[10],
            dosage_text=row[11],
            status=row[12],
            meal_confirmation=row[13],
            sent_at=_parse_datetime(row[14]),
            ack_at=_parse_datetime(row[15]),
        )

    def list_reminder_events(self, user_id: str) -> list[ReminderEvent]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, reminder_definition_id, occurrence_id, regimen_id, reminder_type, title, body, medication_name, scheduled_at, slot, dosage_text, status, meal_confirmation, sent_at, ack_at
                FROM reminder_events WHERE user_id = ? ORDER BY scheduled_at
                """,
                (user_id,),
            ).fetchall()
        events = [
            ReminderEvent(
                id=r[0],
                user_id=r[1],
                reminder_definition_id=r[2],
                occurrence_id=r[3],
                regimen_id=r[4],
                reminder_type=r[5],
                title=r[6],
                body=r[7],
                medication_name=r[8],
                scheduled_at=cast(datetime, _parse_datetime(r[9])),
                slot=r[10],
                dosage_text=r[11],
                status=r[12],
                meal_confirmation=r[13],
                sent_at=_parse_datetime(r[14]),
                ack_at=_parse_datetime(r[15]),
            )
            for r in rows
        ]
        logger.debug("list_reminder_events user_id=%s count=%s", user_id, len(events))
        return events

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
        return self.list_reminder_notification_preferences(
            user_id=user_id, scope_type=scope_type, scope_key=scope_key
        )

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
                created_at=cast(datetime, _parse_datetime(row[7])),
                updated_at=cast(datetime, _parse_datetime(row[8])),
            )
            for row in rows
        ]

    def save_scheduled_notification(
        self, item: ScheduledReminderNotification
    ) -> ScheduledReminderNotification:
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
                    (item.next_attempt_at.isoformat() if item.next_attempt_at else None),
                    item.queued_at.isoformat() if item.queued_at else None,
                    (item.delivered_at.isoformat() if item.delivered_at else None),
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

    def get_scheduled_notification(
        self, notification_id: str
    ) -> ScheduledReminderNotification | None:
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
            trigger_at=cast(datetime, _parse_datetime(row[4])),
            offset_minutes=row[5],
            preference_id=row[6],
            status=row[7],
            attempt_count=row[8],
            next_attempt_at=_parse_datetime(row[9]),
            queued_at=_parse_datetime(row[10]),
            delivered_at=_parse_datetime(row[11]),
            last_error=row[12],
            payload=json.loads(cast(str, row[13])),
            idempotency_key=row[14],
            created_at=cast(datetime, _parse_datetime(row[15])),
            updated_at=cast(datetime, _parse_datetime(row[16])),
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
                trigger_at=cast(datetime, _parse_datetime(row[4])),
                offset_minutes=row[5],
                preference_id=row[6],
                status=row[7],
                attempt_count=row[8],
                next_attempt_at=_parse_datetime(row[9]),
                queued_at=_parse_datetime(row[10]),
                delivered_at=_parse_datetime(row[11]),
                last_error=row[12],
                payload=json.loads(cast(str, row[13])),
                idempotency_key=row[14],
                created_at=cast(datetime, _parse_datetime(row[15])),
                updated_at=cast(datetime, _parse_datetime(row[16])),
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

    def set_scheduled_notification_trigger_at(
        self, notification_id: str, trigger_at: datetime
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE scheduled_notifications
                SET trigger_at = ?, next_attempt_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    trigger_at.isoformat(),
                    trigger_at.isoformat(),
                    datetime.now(UTC).isoformat(),
                    notification_id,
                ),
            )
            conn.commit()

    def mark_scheduled_notification_processing(
        self, notification_id: str, attempt_count: int
    ) -> None:
        now = datetime.now(UTC)
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

    def mark_scheduled_notification_delivered(
        self, notification_id: str, attempt_count: int
    ) -> None:
        now = datetime.now(UTC)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE scheduled_notifications
                SET status = 'delivered', attempt_count = ?, delivered_at = ?, updated_at = ?, last_error = NULL
                WHERE id = ?
                """,
                (
                    attempt_count,
                    now.isoformat(),
                    now.isoformat(),
                    notification_id,
                ),
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
        now = datetime.now(UTC)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE scheduled_notifications
                SET status = 'retry_scheduled', attempt_count = ?, next_attempt_at = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    attempt_count,
                    next_attempt_at.isoformat(),
                    error,
                    now.isoformat(),
                    notification_id,
                ),
            )
            conn.commit()

    def mark_scheduled_notification_dead_letter(
        self,
        notification_id: str,
        *,
        attempt_count: int,
        error: str,
    ) -> None:
        now = datetime.now(UTC)
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
        now = datetime.now(UTC)
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

    def append_notification_log(
        self, entry: ReminderNotificationLogEntry
    ) -> ReminderNotificationLogEntry:
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

    def list_reminder_notification_endpoints(
        self, *, user_id: str
    ) -> list[ReminderNotificationEndpoint]:
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
                created_at=cast(datetime, _parse_datetime(row[5])),
                updated_at=cast(datetime, _parse_datetime(row[6])),
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
            created_at=cast(datetime, _parse_datetime(row[5])),
            updated_at=cast(datetime, _parse_datetime(row[6])),
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
                created_at=cast(datetime, _parse_datetime(row[9])),
            )
            for row in rows
        ]

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

    def save_mobility_reminder_settings(
        self, settings: MobilityReminderSettings
    ) -> MobilityReminderSettings:
        payload = settings.model_dump(mode="json")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO mobility_reminder_settings (user_id, updated_at, payload_json)
                VALUES (?, ?, ?)
                """,
                (
                    settings.user_id,
                    str(payload["updated_at"]),
                    json.dumps(payload),
                ),
            )
            conn.commit()
        return settings
