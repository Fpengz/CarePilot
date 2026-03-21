"""
Load health metrics parsed from chat memory.

This adapter reads metric data stored by the chat health tracker in
data/runtime/chat_memory.db and exposes typed readings.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

from care_pilot.features.companion.core.health.models import BloodPressureReading
from care_pilot.platform.persistence.sqlite_db import get_connection

BASE_DIR = Path(__file__).resolve().parents[5]
DEFAULT_DB_PATH = BASE_DIR / "data" / "runtime" / "chat_memory.db"


class ChatHealthMetricsRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or DEFAULT_DB_PATH

    def list_blood_pressure_readings(
        self,
        *,
        user_id: str,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[BloodPressureReading]:
        if not self._db_path.exists():
            return []
        query = (
            "SELECT message_id, metric_type, value, recorded_at "
            "FROM health_parsed_metrics "
            "WHERE user_id = ? "
            "AND metric_type IN ('blood_pressure_systolic', 'blood_pressure_diastolic')"
        )
        params: list[object] = [user_id]
        if start_at is not None:
            query += " AND recorded_at >= ?"
            params.append(start_at.isoformat())
        if end_at is not None:
            query += " AND recorded_at <= ?"
            params.append(end_at.isoformat())
        query += " ORDER BY recorded_at ASC"
        with get_connection(str(self._db_path)) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        grouped: dict[int, dict[str, object]] = {}
        for message_id, metric_type, value, recorded_at in rows:
            if message_id not in grouped:
                grouped[message_id] = {
                    "recorded_at": recorded_at,
                    "systolic": None,
                    "diastolic": None,
                }
            if metric_type == "blood_pressure_systolic":
                grouped[message_id]["systolic"] = float(value)
            elif metric_type == "blood_pressure_diastolic":
                grouped[message_id]["diastolic"] = float(value)

        readings: list[BloodPressureReading] = []
        for payload in grouped.values():
            systolic = payload.get("systolic")
            diastolic = payload.get("diastolic")
            recorded_at = payload.get("recorded_at")
            if systolic is None or diastolic is None or not recorded_at:
                continue
            try:
                timestamp = datetime.fromisoformat(str(recorded_at))
            except ValueError:
                continue
            readings.append(
                BloodPressureReading(
                    recorded_at=timestamp,
                    systolic=float(cast(float, systolic)),
                    diastolic=float(cast(float, diastolic)),
                )
            )
        readings.sort(key=lambda item: item.recorded_at)
        return readings


__all__ = ["ChatHealthMetricsRepository"]
