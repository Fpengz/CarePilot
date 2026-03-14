"""
Persist workflow metadata in SQLite.

This module implements SQLite storage for workflow tool policies, contract
policies and timeline events.
"""

import json
import sqlite3
from datetime import datetime
from typing import Any, cast

from dietary_guardian.platform.observability.setup import get_logger
from dietary_guardian.platform.observability.workflows.domain.models import (
    ToolRolePolicyRecord,
    WorkflowTimelineEvent,
)

logger = get_logger(__name__)


class SQLiteWorkflowRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

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

    def save_workflow_timeline_event(self, event: WorkflowTimelineEvent) -> WorkflowTimelineEvent:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO workflow_timeline_events
                (event_id, event_type, workflow_name, request_id, correlation_id, user_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.workflow_name,
                    event.request_id,
                    event.correlation_id,
                    event.user_id,
                    json.dumps(event.payload),
                    event.created_at.isoformat(),
                ),
            )
            conn.commit()
        return event

    def list_workflow_timeline_events(
        self,
        *,
        correlation_id: str | None = None,
        user_id: str | None = None,
    ) -> list[WorkflowTimelineEvent]:
        query = (
            "SELECT event_id, event_type, workflow_name, request_id, correlation_id, user_id, payload_json, created_at "
            "FROM workflow_timeline_events WHERE 1=1"
        )
        params: list[Any] = []
        if correlation_id is not None:
            query += " AND correlation_id = ?"
            params.append(correlation_id)
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        query += " ORDER BY created_at"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            WorkflowTimelineEvent(
                event_id=row[0],
                event_type=row[1],
                workflow_name=row[2],
                request_id=row[3],
                correlation_id=row[4],
                user_id=row[5],
                payload=cast(dict[str, object], json.loads(cast(str, row[6]))),
                created_at=datetime.fromisoformat(row[7]),
            )
            for row in rows
        ]
