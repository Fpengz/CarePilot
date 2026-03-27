"""
Persist reminder occurrences in SQLite.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast

from care_pilot.features.reminders.domain.models import (
    ReminderActionRecord,
    ReminderEvent,
    ReminderOccurrence,
)
from care_pilot.platform.observability import get_logger

from .base import SQLiteReminderRepositoryBase, parse_datetime

logger = get_logger(__name__)


class ReminderOccurrenceRepository(SQLiteReminderRepositoryBase):
    def save_reminder_occurrence(self, occurrence: ReminderOccurrence) -> ReminderOccurrence:
        payload = occurrence.model_dump(mode="json")
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
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
            scheduled_for=cast(datetime, parse_datetime(row[3])),
            trigger_at=cast(datetime, parse_datetime(row[4])),
            status=row[5],
            action=row[6],
            action_outcome=row[7],
            acted_at=parse_datetime(row[8]),
            grace_window_minutes=row[9],
            retry_count=row[10],
            last_delivery_status=row[11],
            metadata=json.loads(cast(str, row[12])),
            created_at=cast(datetime, parse_datetime(row[13])),
            updated_at=cast(datetime, parse_datetime(row[14])),
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
        with self._get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            ReminderOccurrence(
                id=row[0],
                reminder_definition_id=row[1],
                user_id=row[2],
                scheduled_for=cast(datetime, parse_datetime(row[3])),
                trigger_at=cast(datetime, parse_datetime(row[4])),
                status=row[5],
                action=row[6],
                action_outcome=row[7],
                acted_at=parse_datetime(row[8]),
                grace_window_minutes=row[9],
                retry_count=row[10],
                last_delivery_status=row[11],
                metadata=json.loads(cast(str, row[12])),
                created_at=cast(datetime, parse_datetime(row[13])),
                updated_at=cast(datetime, parse_datetime(row[14])),
            )
            for row in rows
        ]

    def append_reminder_action(self, action: ReminderActionRecord) -> ReminderActionRecord:
        payload = action.model_dump(mode="json")
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            ReminderActionRecord(
                id=row[0],
                occurrence_id=row[1],
                reminder_definition_id=row[2],
                user_id=row[3],
                action=row[4],
                acted_at=cast(datetime, parse_datetime(row[5])),
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
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
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
            scheduled_at=cast(datetime, parse_datetime(row[9])),
            slot=row[10],
            dosage_text=row[11],
            status=row[12],
            meal_confirmation=row[13],
            sent_at=parse_datetime(row[14]),
            ack_at=parse_datetime(row[15]),
        )

    def list_reminder_events(self, user_id: str) -> list[ReminderEvent]:
        with self._get_connection() as conn:
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
                scheduled_at=cast(datetime, parse_datetime(r[9])),
                slot=r[10],
                dosage_text=r[11],
                status=r[12],
                meal_confirmation=r[13],
                sent_at=parse_datetime(r[14]),
                ack_at=parse_datetime(r[15]),
            )
            for r in rows
        ]
        logger.debug("list_reminder_events user_id=%s count=%s", user_id, len(events))
        return events
