"""SQLite persistence for reminders, scheduled notifications, and endpoints."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, cast

from dietary_guardian.features.reminders.domain.models import (
    MobilityReminderSettings,
    ReminderEvent,
    ReminderNotificationEndpoint,
    ReminderNotificationLogEntry,
    ReminderNotificationPreference,
    ScheduledReminderNotification,
)
from dietary_guardian.platform.observability.setup import get_logger

logger = get_logger(__name__)


class SQLiteReminderRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

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
