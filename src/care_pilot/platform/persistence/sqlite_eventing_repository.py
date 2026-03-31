"""Persist projection sections and reaction execution records in SQLite."""

from __future__ import annotations

import json
from datetime import datetime
from typing import cast

from care_pilot.platform.eventing.models import (
    EventHandlerCursorRecord,
    ExecutionStatus,
    OrderingScope,
    ReactionExecutionRecord,
    SnapshotSectionRecord,
)
from care_pilot.platform.persistence.sqlite_db import get_connection


class SQLiteEventingRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def save_reaction_execution(self, record: ReactionExecutionRecord) -> ReactionExecutionRecord:
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO event_reaction_executions
                (
                    event_id, handler_name, status, started_at, completed_at, failure_count,
                    last_error, payload_hash, event_version, ordering_scope, next_retry_at,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (event_id, handler_name) DO UPDATE SET
                    status = excluded.status,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    failure_count = excluded.failure_count,
                    last_error = excluded.last_error,
                    payload_hash = excluded.payload_hash,
                    event_version = excluded.event_version,
                    ordering_scope = excluded.ordering_scope,
                    next_retry_at = excluded.next_retry_at,
                    updated_at = excluded.updated_at
                """,
                (
                    record.event_id,
                    record.handler_name,
                    record.status,
                    record.started_at.isoformat() if record.started_at else None,
                    record.completed_at.isoformat() if record.completed_at else None,
                    record.failure_count,
                    record.last_error,
                    record.payload_hash,
                    record.event_version,
                    record.ordering_scope,
                    record.next_retry_at.isoformat() if record.next_retry_at else None,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
            conn.commit()
        return record

    def get_reaction_execution(
        self, *, event_id: str, handler_name: str
    ) -> ReactionExecutionRecord | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT event_id, handler_name, status, started_at, completed_at, failure_count,
                       last_error, payload_hash, event_version, ordering_scope, next_retry_at,
                       created_at, updated_at
                FROM event_reaction_executions
                WHERE event_id = ? AND handler_name = ?
                """,
                (event_id, handler_name),
            ).fetchone()
        if row is None:
            return None
        return ReactionExecutionRecord(
            event_id=row[0],
            handler_name=row[1],
            status=ExecutionStatus(cast(str, row[2])),
            started_at=datetime.fromisoformat(row[3]) if row[3] else None,
            completed_at=datetime.fromisoformat(row[4]) if row[4] else None,
            failure_count=int(row[5]),
            last_error=row[6],
            payload_hash=row[7],
            event_version=row[8],
            ordering_scope=OrderingScope(cast(str, row[9])),
            next_retry_at=datetime.fromisoformat(row[10]) if row[10] else None,
            created_at=datetime.fromisoformat(row[11]),
            updated_at=datetime.fromisoformat(row[12]),
        )

    def upsert_snapshot_section(self, record: SnapshotSectionRecord) -> SnapshotSectionRecord:
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO case_snapshot_sections
                (
                    user_id, section_key, payload_json, schema_version,
                    projection_version, source_event_cursor, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (user_id, section_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    schema_version = excluded.schema_version,
                    projection_version = excluded.projection_version,
                    source_event_cursor = excluded.source_event_cursor,
                    updated_at = excluded.updated_at
                """,
                (
                    record.user_id,
                    record.section_key,
                    json.dumps(record.payload),
                    record.schema_version,
                    record.projection_version,
                    record.source_event_cursor,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
            conn.commit()
        return record

    def get_snapshot_section(
        self, *, user_id: str, section_key: str
    ) -> SnapshotSectionRecord | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT user_id, section_key, payload_json, schema_version,
                       projection_version, source_event_cursor, created_at, updated_at
                FROM case_snapshot_sections
                WHERE user_id = ? AND section_key = ?
                """,
                (user_id, section_key),
            ).fetchone()
        if row is None:
            return None
        return SnapshotSectionRecord(
            user_id=row[0],
            section_key=row[1],
            payload=cast(dict[str, object], json.loads(cast(str, row[2]))),
            schema_version=row[3],
            projection_version=row[4],
            source_event_cursor=row[5],
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7]),
        )

    def list_snapshot_sections(self, *, user_id: str) -> list[SnapshotSectionRecord]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT user_id, section_key, payload_json, schema_version,
                       projection_version, source_event_cursor, created_at, updated_at
                FROM case_snapshot_sections
                WHERE user_id = ?
                ORDER BY section_key
                """,
                (user_id,),
            ).fetchall()
        return [
            SnapshotSectionRecord(
                user_id=row[0],
                section_key=row[1],
                payload=cast(dict[str, object], json.loads(cast(str, row[2]))),
                schema_version=row[3],
                projection_version=row[4],
                source_event_cursor=row[5],
                created_at=datetime.fromisoformat(row[6]),
                updated_at=datetime.fromisoformat(row[7]),
            )
            for row in rows
        ]

    def upsert_event_handler_cursor(
        self, record: EventHandlerCursorRecord
    ) -> EventHandlerCursorRecord:
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO event_handler_cursors
                (handler_name, scope_key, last_event_id, last_event_time, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (handler_name, scope_key) DO UPDATE SET
                    last_event_id = excluded.last_event_id,
                    last_event_time = excluded.last_event_time,
                    updated_at = excluded.updated_at
                """,
                (
                    record.handler_name,
                    record.scope_key,
                    record.last_event_id,
                    record.last_event_time.isoformat() if record.last_event_time else None,
                    record.updated_at.isoformat(),
                ),
            )
            conn.commit()
        return record

    def get_event_handler_cursor(
        self, *, handler_name: str, scope_key: str
    ) -> EventHandlerCursorRecord | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT handler_name, scope_key, last_event_id, last_event_time, updated_at
                FROM event_handler_cursors
                WHERE handler_name = ? AND scope_key = ?
                """,
                (handler_name, scope_key),
            ).fetchone()
        if row is None:
            return None
        return EventHandlerCursorRecord(
            handler_name=row[0],
            scope_key=row[1],
            last_event_id=row[2],
            last_event_time=datetime.fromisoformat(row[3]) if row[3] else None,
            updated_at=datetime.fromisoformat(row[4]),
        )

    def list_event_handler_cursors(self) -> list[EventHandlerCursorRecord]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT handler_name, scope_key, last_event_id, last_event_time, updated_at
                FROM event_handler_cursors
                ORDER BY handler_name, scope_key
                """
            ).fetchall()
        return [
            EventHandlerCursorRecord(
                handler_name=row[0],
                scope_key=row[1],
                last_event_id=row[2],
                last_event_time=datetime.fromisoformat(row[3]) if row[3] else None,
                updated_at=datetime.fromisoformat(row[4]),
            )
            for row in rows
        ]


__all__ = ["SQLiteEventingRepository"]
