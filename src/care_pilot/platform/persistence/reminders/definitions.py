"""
Persist reminder definitions in SQLite.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, cast

from care_pilot.features.reminders.domain.models import ReminderDefinition, ReminderScheduleRule

from .base import SQLiteReminderRepositoryBase, parse_datetime


class ReminderDefinitionRepository(SQLiteReminderRepositoryBase):
    def save_reminder_definition(self, definition: ReminderDefinition) -> ReminderDefinition:
        payload = definition.model_dump(mode="json")
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
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
            created_at=cast(datetime, parse_datetime(row[17])),
            updated_at=cast(datetime, parse_datetime(row[18])),
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
        with self._get_connection() as conn:
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
                created_at=cast(datetime, parse_datetime(row[17])),
                updated_at=cast(datetime, parse_datetime(row[18])),
            )
            for row in rows
        ]
