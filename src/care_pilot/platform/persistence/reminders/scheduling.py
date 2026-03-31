"""
Persist scheduled notifications in SQLite.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast

from care_pilot.features.reminders.domain.models import MessageLogEntry, ScheduledMessage

from .base import SQLiteReminderRepositoryBase, parse_datetime


class ReminderSchedulingRepository(SQLiteReminderRepositoryBase):
    def save_scheduled_notification(
        self, item: ScheduledMessage
    ) -> ScheduledMessage:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO scheduled_messages
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
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM scheduled_messages WHERE idempotency_key = ?",
                    (item.idempotency_key,),
                ).fetchone()
            if row is not None:
                existing = self.get_scheduled_notification(str(row[0]))
        if existing is None:
            raise RuntimeError(f"failed to persist scheduled notification {item.id}")
        return existing

    def get_scheduled_notification(
        self, notification_id: str
    ) -> ScheduledMessage | None:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, reminder_id, user_id, channel, trigger_at, offset_minutes, preference_id, status,
                       attempt_count, next_attempt_at, queued_at, delivered_at, last_error, payload_json,
                       idempotency_key, created_at, updated_at
                FROM scheduled_messages
                WHERE id = ?
                """,
                (notification_id,),
            ).fetchone()
        if row is None:
            return None
        return ScheduledMessage(
            id=row[0],
            reminder_id=row[1],
            user_id=row[2],
            channel=row[3],
            trigger_at=cast(datetime, parse_datetime(row[4])),
            offset_minutes=row[5],
            preference_id=row[6],
            status=row[7],
            attempt_count=row[8],
            next_attempt_at=parse_datetime(row[9]),
            queued_at=parse_datetime(row[10]),
            delivered_at=parse_datetime(row[11]),
            last_error=row[12],
            payload=json.loads(cast(str, row[13])),
            idempotency_key=row[14],
            created_at=cast(datetime, parse_datetime(row[15])),
            updated_at=cast(datetime, parse_datetime(row[16])),
        )

    def list_scheduled_messages(
        self,
        *,
        reminder_id: str | None = None,
        user_id: str | None = None,
    ) -> list[ScheduledMessage]:
        query = (
            "SELECT id, reminder_id, user_id, channel, trigger_at, offset_minutes, preference_id, status, "
            "attempt_count, next_attempt_at, queued_at, delivered_at, last_error, payload_json, "
            "idempotency_key, created_at, updated_at FROM scheduled_messages WHERE 1=1"
        )
        params: list[Any] = []
        if reminder_id is not None:
            query += " AND reminder_id = ?"
            params.append(reminder_id)
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        query += " ORDER BY trigger_at, channel"
        with self._get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            ScheduledMessage(
                id=row[0],
                reminder_id=row[1],
                user_id=row[2],
                channel=row[3],
                trigger_at=cast(datetime, parse_datetime(row[4])),
                offset_minutes=row[5],
                preference_id=row[6],
                status=row[7],
                attempt_count=row[8],
                next_attempt_at=parse_datetime(row[9]),
                queued_at=parse_datetime(row[10]),
                delivered_at=parse_datetime(row[11]),
                last_error=row[12],
                payload=json.loads(cast(str, row[13])),
                idempotency_key=row[14],
                created_at=cast(datetime, parse_datetime(row[15])),
                updated_at=cast(datetime, parse_datetime(row[16])),
            )
            for row in rows
        ]

    def lease_due_scheduled_messages(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> list[ScheduledMessage]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id
                FROM scheduled_messages
                WHERE status IN ('pending', 'retry_scheduled')
                  AND COALESCE(next_attempt_at, trigger_at) <= ?
                ORDER BY COALESCE(next_attempt_at, trigger_at), channel
                LIMIT ?
                """,
                (now.isoformat(), limit),
            ).fetchall()
            leased: list[ScheduledMessage] = []
            for (notification_id,) in rows:
                updated = conn.execute(
                    """
                    UPDATE scheduled_messages
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
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE scheduled_messages
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
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE scheduled_messages
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
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE scheduled_messages
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
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE scheduled_messages
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
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE scheduled_messages
                SET status = 'dead_letter', attempt_count = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (attempt_count, error, now.isoformat(), notification_id),
            )
            conn.commit()

    def cancel_scheduled_messages_for_reminder(self, reminder_id: str) -> int:
        now = datetime.now(UTC)
        with self._get_connection() as conn:
            result = conn.execute(
                """
                UPDATE scheduled_messages
                SET status = 'cancelled', updated_at = ?
                WHERE reminder_id = ? AND status IN ('pending', 'queued', 'processing', 'retry_scheduled')
                """,
                (now.isoformat(), reminder_id),
            )
            conn.commit()
        return int(result.rowcount)

    def append_notification_log(
        self, entry: MessageLogEntry
    ) -> MessageLogEntry:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO message_logs
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

    def list_message_logs(
        self,
        *,
        reminder_id: str | None = None,
        scheduled_notification_id: str | None = None,
    ) -> list[MessageLogEntry]:
        query = (
            "SELECT id, scheduled_notification_id, reminder_id, user_id, channel, attempt_number, event_type, "
            "error_message, metadata_json, created_at FROM message_logs WHERE 1=1"
        )
        params: list[Any] = []
        if reminder_id is not None:
            query += " AND reminder_id = ?"
            params.append(reminder_id)
        if scheduled_notification_id is not None:
            query += " AND scheduled_notification_id = ?"
            params.append(scheduled_notification_id)
        query += " ORDER BY created_at"
        with self._get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            MessageLogEntry(
                id=row[0],
                scheduled_notification_id=row[1],
                reminder_id=row[2],
                user_id=row[3],
                channel=row[4],
                attempt_number=row[5],
                event_type=row[6],
                error_message=row[7],
                metadata=json.loads(cast(str, row[8])),
                created_at=cast(datetime, parse_datetime(row[9])),
            )
            for row in rows
        ]
