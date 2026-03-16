"""
Extract and chart health metrics from tracked chat messages.

This module parses `[TRACK]` messages, extracts metric values (with LLM
assistance), caches the results, and builds chart-ready series for the
health dashboard.
"""

from __future__ import annotations

import asyncio
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless — no display needed
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from care_pilot.agent.chat.schemas import ChatMetricsOutput
from care_pilot.agent.runtime.inference_types import (
    InferenceModality,
    InferenceRequest,
)
from care_pilot.features.companion.chat.memory import InferenceEngineProtocol
from care_pilot.platform.observability import get_logger

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[4]
DB_PATH = BASE_DIR / "data" / "runtime" / "chat_memory.db"

_PARSE_PROMPT = """\
The user sent a health-tracking message. Extract every numeric health metric \
from the text and return a list of metric entries in the `metrics` field.

Each element must have:
  "metric_type" : one of:
      weight | blood_pressure_systolic | blood_pressure_diastolic |
      blood_glucose | hba1c | heart_rate |
      cholesterol_total | cholesterol_ldl | cholesterol_hdl |
      symptom_severity
  "value"       : numeric value as a float
  "unit"        : unit string (e.g. "kg", "mmHg", "mmol/L", "bpm", "%") or null
  "label"       : short human-readable name for the chart legend
                  (e.g. "Weight", "Systolic BP", "Blood Glucose (fasting)")

Rules:
- For blood pressure "140/90": emit TWO entries (systolic 140, diastolic 90).
- For symptom_severity use the number the user gives (e.g. "7/10" → 7.0).
- Omit any metric whose value cannot be a number.
- If nothing numeric is found, return an empty list.

Return only the `metrics` field.
"""


# ---------------------------------------------------------------------------
# HealthTracker
# ---------------------------------------------------------------------------


class HealthTracker:
    """
    Reads [TRACK] messages from SQLite, parses them with the LLM (cached),
    and renders matplotlib line charts for the dashboard.
    """

    def __init__(
        self,
        user_id: str,
        session_id: str,
        inference_engine: InferenceEngineProtocol,
        db_path: Path = DB_PATH,
    ) -> None:
        self._user_id = user_id
        self._session_id = session_id
        self._engine = inference_engine
        self._db_path = db_path
        self._logger = get_logger(__name__)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._logger.info(
            "chat_health_tracker_ready user_id=%s session=%s",
            user_id,
            session_id,
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def build_chart(self, start_date: str, end_date: str):
        """
        Return a matplotlib Figure plotting all [TRACK] metrics in [start_date, end_date].
        Dates should be "YYYY-MM-DD" strings.
        """
        messages = self._get_tracked_messages(start_date, end_date)

        if not messages:
            return self._empty_figure(
                f"No [TRACK] entries found between {start_date} and {end_date}.\n\n"
                "Tip: prefix your message with [TRACK] to log a metric, e.g.\n"
                "[TRACK] weight 78.5 kg"
            )

        # Parse each message (DB-cached after first parse)
        all_metrics: list[dict] = []
        for msg in messages:
            parsed = self._parse_and_cache(msg["id"], msg["content"], msg["created_at"])
            all_metrics.extend(parsed)

        if not all_metrics:
            return self._empty_figure(
                "[TRACK] messages found but no numeric values could be extracted.\n"
                "Make sure to include a number, e.g. [TRACK] weight 80 kg"
            )

        return self._render_chart(all_metrics, start_date, end_date)

    def get_raw_entries(self, start_date: str, end_date: str) -> list[dict]:
        """Return raw [TRACK] messages in the date range (for table display)."""
        return self._get_tracked_messages(start_date, end_date)

    def get_chart_data(self, start_date: str, end_date: str) -> dict:
        """
        Return parsed metric data as a JSON-serialisable dict for Recharts.

        Shape:
        {
          "metrics": {
            "weight": {
              "label": "Weight", "unit": "kg",
              "data": [{"date": "2026-03-01T10:00:00", "value": 80.5}, ...]
            },
            ...
          }
        }
        """
        messages = self._get_tracked_messages(start_date, end_date)
        all_metrics: list[dict] = []
        for msg in messages:
            parsed = self._parse_and_cache(msg["id"], msg["content"], msg["created_at"])
            all_metrics.extend(parsed)

        groups: dict[str, dict] = {}
        for m in all_metrics:
            mt = m["metric_type"]
            if mt not in groups:
                groups[mt] = {
                    "label": m.get("label") or mt.replace("_", " ").title(),
                    "unit": m.get("unit") or "",
                    "data": [],
                }
            groups[mt]["data"].append(
                {
                    "date": m["recorded_at"],
                    "value": float(m["value"]),
                }
            )

        # Sort each series by date
        for g in groups.values():
            g["data"].sort(key=lambda p: p["date"])

        return {"metrics": groups}

    # ------------------------------------------------------------------ #
    # SQLite helpers
    # ------------------------------------------------------------------ #

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            if not _table_has_column(conn, "health_parsed_metrics", "user_id"):
                conn.execute("DROP TABLE IF EXISTS health_parsed_metrics")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS health_parsed_metrics (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id  INTEGER NOT NULL,
                    user_id     TEXT    NOT NULL,
                    session_id  TEXT    NOT NULL,
                    metric_type TEXT    NOT NULL,
                    value       REAL    NOT NULL,
                    unit        TEXT,
                    label       TEXT,
                    recorded_at TEXT    NOT NULL,
                    UNIQUE (message_id, metric_type, user_id)
                )
            """)

    def _get_tracked_messages(self, start_date: str, end_date: str) -> list[dict]:
        """Query chat_messages for [TRACK] user messages within the date window."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, content, created_at
                   FROM chat_messages
                   WHERE user_id = ?
                     AND session_id = ?
                     AND role = 'user'
                     AND content LIKE '[TRACK]%'
                     AND DATE(created_at) BETWEEN ? AND ?
                   ORDER BY created_at ASC""",
                (self._user_id, self._session_id, start_date, end_date),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # LLM parsing with DB cache
    # ------------------------------------------------------------------ #

    def _parse_and_cache(self, message_id: int, content: str, recorded_at: str) -> list[dict]:
        """Return parsed metrics for a message, using cached DB results if available."""
        with self._connect() as conn:
            cached = conn.execute(
                "SELECT * FROM health_parsed_metrics WHERE message_id = ? AND user_id = ?",
                (message_id, self._user_id),
            ).fetchall()
        if cached:
            return [dict(r) for r in cached]

        # Strip [TRACK] prefix before sending to LLM
        text = content[len("[TRACK]") :].strip()
        metrics = self._call_llm(text)
        if not metrics:
            return []

        rows = []
        for m in metrics:
            val = m.get("value")
            if val is None:
                continue
            rows.append(
                {
                    "message_id": message_id,
                    "user_id": self._user_id,
                    "session_id": self._session_id,
                    "metric_type": str(m.get("metric_type", "unknown")).strip(),
                    "value": float(val),
                    "unit": m.get("unit"),
                    "label": m.get("label") or m.get("metric_type", "unknown"),
                    "recorded_at": recorded_at,
                }
            )

        if rows:
            with self._connect() as conn:
                conn.executemany(
                    """INSERT OR IGNORE INTO health_parsed_metrics
                           (message_id, user_id, session_id, metric_type, value, unit, label, recorded_at)
                       VALUES
                           (:message_id, :user_id, :session_id, :metric_type, :value, :unit, :label, :recorded_at)""",
                    rows,
                )
            self._logger.info(
                "chat_health_metrics_cached message_id=%s count=%s",
                message_id,
                len(rows),
            )

        return rows

    def _call_llm(self, text: str) -> list[dict]:
        """Ask the LLM to extract metrics. Returns [] on failure."""
        try:
            request = InferenceRequest(
                request_id=str(uuid.uuid4()),
                user_id=self._user_id,
                modality=InferenceModality.TEXT,
                payload={"prompt": text},
                output_schema=ChatMetricsOutput,
                system_prompt=_PARSE_PROMPT,
            )
            response = asyncio.run(self._engine.infer(request))
            return [metric.model_dump() for metric in response.structured_output.metrics]
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("chat_health_metrics_failed error=%s", exc)
            return []

    # ------------------------------------------------------------------ #
    # Chart rendering
    # ------------------------------------------------------------------ #

    def _render_chart(self, all_metrics: list[dict], start_date: str, end_date: str):
        """Build a matplotlib Figure with one subplot per metric_type."""
        # Group by metric_type, sort by time
        groups: dict[str, list[tuple]] = {}
        for m in all_metrics:
            groups.setdefault(m["metric_type"], []).append(
                (
                    datetime.fromisoformat(m["recorded_at"]),
                    float(m["value"]),
                    m.get("unit") or "",
                    m.get("label") or m["metric_type"],
                )
            )
        for pts in groups.values():
            pts.sort(key=lambda p: p[0])

        n = len(groups)
        fig, axes = plt.subplots(
            n,
            1,
            figsize=(10, max(3.5 * n, 4)),
            squeeze=False,
        )
        fig.suptitle(
            f"Health Metrics  ·  {start_date}  →  {end_date}",
            fontsize=13,
            fontweight="bold",
            y=1.01,
        )

        for ax, (_metric_type, pts) in zip(axes[:, 0], groups.items(), strict=False):
            dates = [p[0] for p in pts]
            values = [p[1] for p in pts]
            label = pts[0][3]
            unit = pts[0][2]

            ax.plot(
                dates,
                values,
                marker="o",
                linewidth=2,
                markersize=7,
                color="#2563eb",
            )
            ax.fill_between(dates, values, alpha=0.08, color="#2563eb")
            ax.set_title(label, fontsize=11, fontweight="bold", pad=6)
            ax.set_ylabel(unit, fontsize=9)
            ax.grid(True, linestyle="--", alpha=0.4)

            # Format x-axis
            if len(dates) > 1:
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
                fig.autofmt_xdate(rotation=30, ha="right")
            else:
                ax.set_xticks(dates)
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %H:%M"))

            # Annotate each point with its value
            for d, v in zip(dates, values, strict=False):
                ax.annotate(
                    f"{v:g} {unit}".strip(),
                    (d, v),
                    textcoords="offset points",
                    xytext=(0, 10),
                    ha="center",
                    fontsize=8,
                    color="#1e3a8a",
                )

        plt.tight_layout()
        return fig

    @staticmethod
    def _empty_figure(message: str):
        """Return a blank figure with a centred message."""
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=11,
            color="#6b7280",
            wrap=True,
        )
        ax.set_axis_off()
        plt.tight_layout()
        return fig


def _table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)
