"""
agents/health_tracker.py
------------------------
Parses [TRACK] messages stored in chat_memory.db and builds line charts
for the Health Dashboard tab.

Users prefix chat messages with [TRACK] to log numeric health metrics:
    [TRACK] I weighed 80kg today
    [TRACK] blood pressure 140/90 mmHg
    [TRACK] fasting blood glucose 7.2 mmol/L
    [TRACK] felt really fatigued, severity 7/10

How it works
------------
1. Query chat_messages WHERE content LIKE '[TRACK]%' in the chosen date range.
2. For each message, call the LLM to extract metric_type / value / unit.
   Results are cached in health_parsed_metrics so no message is re-parsed.
3. Group by metric_type and plot one subplot per metric as a line chart.

Supported metric_type values (from LLM):
    weight                   — kg / lbs
    blood_pressure_systolic  — mmHg
    blood_pressure_diastolic — mmHg
    blood_glucose            — mmol/L / mg/dL
    hba1c                    — %
    heart_rate               — bpm
    cholesterol_total        — mmol/L
    cholesterol_ldl          — mmol/L
    cholesterol_hdl          — mmol/L
    symptom_severity         — 1–10

Usage:
    tracker = HealthTracker(session_id="default", client=openai_client, model_id=...)
    fig = tracker.build_chart("2026-01-01", "2026-03-31")
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib
matplotlib.use("Agg")          # headless — no display needed
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

if TYPE_CHECKING:
    from openai import OpenAI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "vectorstore" / "chat_memory.db"

_PARSE_PROMPT = """\
The user sent a health-tracking message. Extract every numeric health metric \
from the text and return a JSON array.

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
- If nothing numeric is found, return exactly: []

Reply with ONLY the JSON array, no markdown, no explanation.
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
        session_id: str,
        client: "OpenAI",
        model_id: str,
        db_path: Path = DB_PATH,
    ) -> None:
        self._session_id = session_id
        self._client     = client
        self._model_id   = model_id
        self._db_path    = db_path
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        print(f"[HealthTracker] Initialised — session={session_id!r}")

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
                    "unit":  m.get("unit") or "",
                    "data":  [],
                }
            groups[mt]["data"].append({
                "date":  m["recorded_at"],
                "value": float(m["value"]),
            })

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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS health_parsed_metrics (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id  INTEGER NOT NULL,
                    session_id  TEXT    NOT NULL,
                    metric_type TEXT    NOT NULL,
                    value       REAL    NOT NULL,
                    unit        TEXT,
                    label       TEXT,
                    recorded_at TEXT    NOT NULL,
                    UNIQUE (message_id, metric_type)
                )
            """)

    def _get_tracked_messages(self, start_date: str, end_date: str) -> list[dict]:
        """Query chat_messages for [TRACK] user messages within the date window."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, content, created_at
                   FROM chat_messages
                   WHERE session_id = ?
                     AND role = 'user'
                     AND content LIKE '[TRACK]%'
                     AND DATE(created_at) BETWEEN ? AND ?
                   ORDER BY created_at ASC""",
                (self._session_id, start_date, end_date),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # LLM parsing with DB cache
    # ------------------------------------------------------------------ #

    def _parse_and_cache(
        self, message_id: int, content: str, recorded_at: str
    ) -> list[dict]:
        """Return parsed metrics for a message, using cached DB results if available."""
        with self._connect() as conn:
            cached = conn.execute(
                "SELECT * FROM health_parsed_metrics WHERE message_id = ?",
                (message_id,),
            ).fetchall()
        if cached:
            return [dict(r) for r in cached]

        # Strip [TRACK] prefix before sending to LLM
        text = content[len("[TRACK]"):].strip()
        metrics = self._call_llm(text)
        if not metrics:
            return []

        rows = []
        for m in metrics:
            val = m.get("value")
            if val is None:
                continue
            rows.append({
                "message_id":  message_id,
                "session_id":  self._session_id,
                "metric_type": str(m.get("metric_type", "unknown")).strip(),
                "value":       float(val),
                "unit":        m.get("unit"),
                "label":       m.get("label") or m.get("metric_type", "unknown"),
                "recorded_at": recorded_at,
            })

        if rows:
            with self._connect() as conn:
                conn.executemany(
                    """INSERT OR IGNORE INTO health_parsed_metrics
                           (message_id, session_id, metric_type, value, unit, label, recorded_at)
                       VALUES
                           (:message_id, :session_id, :metric_type, :value, :unit, :label, :recorded_at)""",
                    rows,
                )
            print(f"[HealthTracker] Cached {len(rows)} metric(s) for message {message_id}")

        return rows

    def _call_llm(self, text: str) -> list[dict]:
        """Ask the LLM to extract metrics. Returns [] on failure."""
        try:
            resp = self._client.chat.completions.create(
                model=self._model_id,
                messages=[
                    {"role": "system", "content": _PARSE_PROMPT},
                    {"role": "user",   "content": text},
                ],
                temperature=0,
                max_tokens=300,
            )
            raw = resp.choices[0].message.content.strip()
            result = json.loads(raw)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError as exc:
            print(f"[HealthTracker] JSON parse error: {exc}")
            return []
        except Exception as exc:
            print(f"[HealthTracker] LLM error: {exc}")
            return []

    # ------------------------------------------------------------------ #
    # Chart rendering
    # ------------------------------------------------------------------ #

    def _render_chart(
        self, all_metrics: list[dict], start_date: str, end_date: str
    ):
        """Build a matplotlib Figure with one subplot per metric_type."""
        # Group by metric_type, sort by time
        groups: dict[str, list[tuple]] = {}
        for m in all_metrics:
            groups.setdefault(m["metric_type"], []).append((
                datetime.fromisoformat(m["recorded_at"]),
                float(m["value"]),
                m.get("unit") or "",
                m.get("label") or m["metric_type"],
            ))
        for pts in groups.values():
            pts.sort(key=lambda p: p[0])

        n = len(groups)
        fig, axes = plt.subplots(
            n, 1,
            figsize=(10, max(3.5 * n, 4)),
            squeeze=False,
        )
        fig.suptitle(
            f"Health Metrics  ·  {start_date}  →  {end_date}",
            fontsize=13, fontweight="bold", y=1.01,
        )

        for ax, (metric_type, pts) in zip(axes[:, 0], groups.items()):
            dates  = [p[0] for p in pts]
            values = [p[1] for p in pts]
            label  = pts[0][3]
            unit   = pts[0][2]

            ax.plot(dates, values, marker="o", linewidth=2, markersize=7, color="#2563eb")
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
            for d, v in zip(dates, values):
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
            0.5, 0.5, message,
            ha="center", va="center",
            transform=ax.transAxes,
            fontsize=11, color="#6b7280",
            wrap=True,
        )
        ax.set_axis_off()
        plt.tight_layout()
        return fig
