"""
Persist alert outbox records in SQLite.

This module implements SQLite persistence for alert outbox data.
"""

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from care_pilot.features.safety.domain.alerts.models import (
    AlertMessage,
    OutboxRecord,
)
from care_pilot.platform.observability.setup import get_logger

logger = get_logger(__name__)


class SQLiteAlertRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def enqueue_alert(self, message: AlertMessage) -> list[OutboxRecord]:
        created: list[OutboxRecord] = []
        now = datetime.now(UTC)
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
        logger.info(
            "enqueue_alert alert_id=%s sinks=%s",
            message.alert_id,
            message.destinations,
        )
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

    def mark_alert_delivered(
        self, alert_id: str, sink: str, attempt_count: int | None = None
    ) -> None:
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
                (
                    attempt_count,
                    next_attempt_at.isoformat(),
                    error,
                    alert_id,
                    sink,
                ),
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
                    lease_until=(datetime.fromisoformat(row[12]) if row[12] else None),
                    idempotency_key=row[13],
                )
            )
        return out
