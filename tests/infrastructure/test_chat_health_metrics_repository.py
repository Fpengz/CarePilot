"""Tests for chat health metrics repository."""

import sqlite3
from datetime import datetime

from care_pilot.platform.persistence.health_metrics import ChatHealthMetricsRepository


def _setup_db(path: str) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE health_parsed_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT,
                label TEXT,
                recorded_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def test_bp_readings_pair_systolic_and_diastolic(tmp_path) -> None:
    db_path = tmp_path / "chat_memory.db"
    _setup_db(str(db_path))
    recorded = datetime(2026, 3, 10, 8, 0, 0).isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        conn.executemany(
            """
            INSERT INTO health_parsed_metrics
            (message_id, user_id, session_id, metric_type, value, unit, label, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "user-1", "s1", "blood_pressure_systolic", 142, "mmHg", "Systolic", recorded),
                (1, "user-1", "s1", "blood_pressure_diastolic", 88, "mmHg", "Diastolic", recorded),
                (2, "user-1", "s1", "blood_pressure_systolic", 135, "mmHg", "Systolic", recorded),
            ],
        )
        conn.commit()

    repo = ChatHealthMetricsRepository(db_path=db_path)
    readings = repo.list_blood_pressure_readings(user_id="user-1")
    assert len(readings) == 1
    assert readings[0].systolic == 142
    assert readings[0].diastolic == 88
