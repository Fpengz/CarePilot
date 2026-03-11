from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from dietary_guardian.domain.reminders.models import ReminderDispatchResult, ReminderEvent


class SQLiteOutboxRepository:
    """
    SQLite-backed outbox repository for reliable reminder delivery.

    Event status lifecycle:
    - PENDING
    - SENT
    - FAILED
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminder_outbox (
                    event_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    reminder_id TEXT NOT NULL,
                    reminder_type TEXT NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    provider_msg_id TEXT,
                    error_reason TEXT
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_outbox_status_scheduled
                ON reminder_outbox(status, scheduled_at)
                """
            )

            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_outbox_idempotency_key
                ON reminder_outbox(idempotency_key)
                """
            )

    def enqueue(self, event: ReminderEvent) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO reminder_outbox (
                    event_id, user_id, reminder_id, reminder_type,
                    scheduled_at, channel, payload, idempotency_key,
                    correlation_id, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
                """,
                (
                    event.event_id,
                    event.user_id,
                    event.reminder_id,
                    event.reminder_type.value,
                    event.scheduled_at,
                    event.channel,
                    event.payload,
                    event.idempotency_key,
                    event.correlation_id,
                    event.created_at,
                ),
            )

    def fetch_due_events(self, now: str, limit: int = 50) -> list[ReminderEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM reminder_outbox
                WHERE status = 'PENDING' AND scheduled_at <= ?
                ORDER BY scheduled_at ASC, created_at ASC
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()

        return [
            ReminderEvent(
                event_id=row["event_id"],
                user_id=row["user_id"],
                reminder_id=row["reminder_id"],
                reminder_type=row["reminder_type"],  # type: ignore[arg-type]
                scheduled_at=row["scheduled_at"],
                channel=row["channel"],
                payload=row["payload"],
                idempotency_key=row["idempotency_key"],
                correlation_id=row["correlation_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def mark_sent(self, event_id: str, provider_msg_id: Optional[str] = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE reminder_outbox
                SET status = 'SENT',
                    provider_msg_id = ?,
                    error_reason = NULL
                WHERE event_id = ?
                """,
                (provider_msg_id, event_id),
            )

    def mark_failed(self, event_id: str, reason: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE reminder_outbox
                SET status = 'FAILED',
                    error_reason = ?
                WHERE event_id = ?
                """,
                (reason, event_id),
            )

    def retry_failed(self, *, event_id: Optional[str] = None) -> int:
        with self._connect() as conn:
            if event_id:
                cursor = conn.execute(
                    """
                    UPDATE reminder_outbox
                    SET status = 'PENDING',
                        error_reason = NULL
                    WHERE event_id = ? AND status = 'FAILED'
                    """,
                    (event_id,),
                )
            else:
                cursor = conn.execute(
                    """
                    UPDATE reminder_outbox
                    SET status = 'PENDING',
                        error_reason = NULL
                    WHERE status = 'FAILED'
                    """
                )
            return cursor.rowcount

    def get_event_status(self, event_id: str) -> Optional[dict[str, str | None]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT event_id, status, provider_msg_id, error_reason
                FROM reminder_outbox
                WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "event_id": row["event_id"],
            "status": row["status"],
            "provider_msg_id": row["provider_msg_id"],
            "error_reason": row["error_reason"],
        }