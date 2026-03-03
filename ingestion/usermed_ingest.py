"""
ingestion/usermed-ingest.py
---------------------------
Manages a personal medication schedule database (SQLite).

Why SQLite and not ChromaDB / Postgres?
  • Medication schedules are structured, time-keyed data.
    You query "what meds are due before breakfast?" — that's SQL, not vector search.
  • SQLite is zero-setup, embedded, and ships with Python.
  • Postgres is a server — overkill for a local personal app.

DB schema (user_medications table):
  id               INTEGER  PRIMARY KEY AUTOINCREMENT
  medicine_name    TEXT     NOT NULL
  before_breakfast INTEGER  DEFAULT 0   -- 1 = yes
  after_breakfast  INTEGER  DEFAULT 0
  before_lunch     INTEGER  DEFAULT 0
  after_lunch      INTEGER  DEFAULT 0
  before_dinner    INTEGER  DEFAULT 0
  after_dinner     INTEGER  DEFAULT 0
  dose_notes       TEXT     -- e.g. "1 tablet", "500 mg"
  created_at       TEXT     -- ISO-8601 timestamp

Timing slots (for future reminder integration):
  get_due_medications(slot) — returns meds due at a given slot string,
  e.g. "before_breakfast", keyed to a scheduled time in your reminder service.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "vectorstore" / "user_medications.db"

TIMING_SLOTS = [
    "before_breakfast",
    "after_breakfast",
    "before_lunch",
    "after_lunch",
    "before_dinner",
    "after_dinner",
]

TIMING_LABEL_TO_SLOT = {
    "Before Breakfast": "before_breakfast",
    "After Breakfast":  "after_breakfast",
    "Before Lunch":     "before_lunch",
    "After Lunch":      "after_lunch",
    "Before Dinner":    "before_dinner",
    "After Dinner":     "after_dinner",
}

SLOT_TO_LABEL = {v: k for k, v in TIMING_LABEL_TO_SLOT.items()}


# ===========================================================================
# Database
# ===========================================================================

class UserMedDB:
    """SQLite-backed store for a user's personal medication schedule."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(db_path)
        self._init_schema()

    # ── internals ────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_medications (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    medicine_name    TEXT    NOT NULL,
                    before_breakfast INTEGER NOT NULL DEFAULT 0,
                    after_breakfast  INTEGER NOT NULL DEFAULT 0,
                    before_lunch     INTEGER NOT NULL DEFAULT 0,
                    after_lunch      INTEGER NOT NULL DEFAULT 0,
                    before_dinner    INTEGER NOT NULL DEFAULT 0,
                    after_dinner     INTEGER NOT NULL DEFAULT 0,
                    dose_notes       TEXT,
                    created_at       TEXT    NOT NULL
                )
            """)

    # ── public API ────────────────────────────────────────────────────────

    def add_medication(
        self,
        medicine_name:    str,
        timing_slots:     list[str],      # list of slot keys, e.g. ["before_breakfast"]
        dose_notes:       str = "",
    ) -> int:
        """Insert a new medication row. Returns the new row id."""
        slot_vals = {s: int(s in timing_slots) for s in TIMING_SLOTS}
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO user_medications
                   (medicine_name, before_breakfast, after_breakfast,
                    before_lunch, after_lunch, before_dinner, after_dinner,
                    dose_notes, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    medicine_name.strip(),
                    slot_vals["before_breakfast"],
                    slot_vals["after_breakfast"],
                    slot_vals["before_lunch"],
                    slot_vals["after_lunch"],
                    slot_vals["before_dinner"],
                    slot_vals["after_dinner"],
                    dose_notes.strip(),
                    now,
                ),
            )
            return cur.lastrowid

    def delete_medication(self, row_id: int) -> bool:
        """Delete a medication by id. Returns True if a row was deleted."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM user_medications WHERE id = ?", (row_id,))
            return cur.rowcount > 0

    def list_medications(self) -> list[dict]:
        """Return all medications as a list of dicts."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM user_medications ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_due_medications(self, slot: str) -> list[dict]:
        """
        Fetch meds due at a specific timing slot.

        slot — one of: before_breakfast, after_breakfast, before_lunch,
                        after_lunch, before_dinner, after_dinner

        Typical usage in a reminder service:
            due = db.get_due_medications("before_breakfast")
            for med in due:
                send_notification(f"Time to take {med['medicine_name']}!")
        """
        if slot not in TIMING_SLOTS:
            raise ValueError(f"Unknown slot '{slot}'. Valid: {TIMING_SLOTS}")
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM user_medications WHERE {slot} = 1"
            ).fetchall()
        return [dict(r) for r in rows]

    def to_display_rows(self) -> list[list]:
        """Return data as plain lists for a Gradio Dataframe."""
        meds = self.list_medications()
        rows = []
        for m in meds:
            slots = [SLOT_TO_LABEL[s] for s in TIMING_SLOTS if m[s]]
            rows.append([
                m["id"],
                m["medicine_name"],
                m["dose_notes"] or "—",
                ", ".join(slots) if slots else "—",
                m["created_at"],
            ])
        return rows


# ===========================================================================
# LLM Parser  (SEA-LION via OpenAI-compatible API)
# ===========================================================================

class PrescriptionParser:
    """
    Parses free-text prescription / doctor advice into structured
    medication entries using the SEA-LION LLM.
    """

    SYSTEM_PROMPT = """\
You are a medical prescription parser. Given a doctor's note or patient's description
of their medication schedule in any language (English, Chinese, Malay, Tamil),
extract a JSON array of medication entries.

Each entry must follow this exact schema:
{
  "medicine_name": "<string>",
  "dose_notes": "<string or empty>",
  "timing": ["<slot>", ...]   // slots: before_breakfast, after_breakfast,
                               //         before_lunch, after_lunch,
                               //         before_dinner, after_dinner
}

Rules:
- Include ONLY medications explicitly mentioned.
- If timing is unclear, make your best inference from context (e.g. "三餐后" → after_breakfast, after_lunch, after_dinner).
- Return ONLY the raw JSON array. No extra explanation, no markdown code fences.
"""

    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=os.environ.get("SEALION_API", ""),
            base_url="https://api.sea-lion.ai/v1",
        )
        self._model = os.environ.get("CHAT_MODEL_ID", "aisingapore/Gemma-SEA-LION-v4-27B-IT")

    def parse(self, prescription_text: str) -> list[dict]:
        """
        Send prescription text to SEA-LION and return list of parsed entries.
        Each entry: { medicine_name, dose_notes, timing: [slot, ...] }
        Raises ValueError on LLM or JSON parse failure.
        """
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user",   "content": prescription_text.strip()},
            ],
            temperature=0,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()

        # Strip any accidental markdown fences
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            entries = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON:\n{raw}\n\nError: {e}") from e

        if not isinstance(entries, list):
            raise ValueError(f"Expected JSON array, got: {type(entries)}")

        # Validate & normalise each entry
        cleaned = []
        for entry in entries:
            name   = str(entry.get("medicine_name", "")).strip()
            dose   = str(entry.get("dose_notes", "")).strip()
            timing = [t for t in entry.get("timing", []) if t in TIMING_SLOTS]
            if name:
                cleaned.append({"medicine_name": name, "dose_notes": dose, "timing": timing})
        return cleaned


# ===========================================================================
# Module-level singletons (imported by main.py)
# ===========================================================================

user_med_db = UserMedDB()
prescription_parser = PrescriptionParser()
