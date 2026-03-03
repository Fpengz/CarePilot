"""
agents/memory_manager.py
------------------------
Manages long-term and short-term conversation memory for ChatAgent.

Long-term  : SQLite — every message persisted (vectorstore/chat_memory.db)
Short-term : In-memory list — latest SHORT_TERM_SIZE messages for LLM prompt
Summary    : Rolling summary of all messages before the short-term window,
             stored in SQLite and updated every time SHORT_TERM_SIZE new
             messages "fall out" of the window.

Prompt template produced by build_prompt_context():
    {
        "rolling_summary": str | None,   # None if no summary yet
        "short_term":      list[dict],   # last N {"role", "content"} messages
    }

Usage:
    mem = MemoryManager(session_id="default", client=openai_client, model_id=...)
    mem.add_message("user", "Hello!")
    mem.add_message("assistant", "Hi there!")
    ctx = mem.build_prompt_context()
    # ctx["rolling_summary"] → str or None
    # ctx["short_term"]      → list of last 5 dicts
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SHORT_TERM_SIZE = 3          # messages kept in the prompt window
SUMMARIZE_EVERY = 3          # trigger summarisation after N new out-of-window msgs

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "vectorstore" / "chat_memory.db"

_SUMMARY_PROMPT = """\
You are a conversation summarizer. Given the previous rolling summary and a \
batch of new messages, produce a concise updated summary that captures the \
key topics, facts, and decisions discussed. Do not include greetings or filler. \
Write in third-person ("The user asked…", "The assistant explained…"). \
Reply with ONLY the summary text, no extra commentary.
"""


# ---------------------------------------------------------------------------
# MemoryManager
# ---------------------------------------------------------------------------

class MemoryManager:
    """
    Maintains long-term chat history in SQLite and a short-term window
    (latest SHORT_TERM_SIZE messages) in memory.

    After every SUMMARIZE_EVERY messages leave the short-term window,
    the LLM is called to update the rolling summary.
    """

    def __init__(
        self,
        session_id: str,
        client: "OpenAI",
        model_id: str,
        db_path: Path = DB_PATH,
    ) -> None:
        self._session_id  = session_id
        self._client      = client
        self._model_id    = model_id
        self._db_path     = db_path

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

        # Load persisted state
        self._messages: list[dict]  = self._load_messages()
        self._rolling_summary: str  = self._load_summary()
        self._summarized_up_to: int = self._load_summarized_up_to()

        print(
            f"[MemoryManager] session={session_id!r} | "
            f"loaded {len(self._messages)} messages | "
            f"summarized_up_to={self._summarized_up_to}"
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def add_message(self, role: str, content: str) -> None:
        """Append a message, persist it, and maybe update the rolling summary."""
        msg = {"role": role, "content": content}
        self._messages.append(msg)
        self._persist_message(role, content)
        self._maybe_update_summary()

    def build_prompt_context(self) -> dict:
        """Return the context dict used by ChatAgent to build the LLM prompt."""
        return {
            "rolling_summary": self._rolling_summary or None,
            "short_term":      self._messages[-SHORT_TERM_SIZE:],
        }

    def all_messages(self) -> list[dict]:
        """Return every message (for Gradio chatbot display)."""
        return list(self._messages)

    @property
    def rolling_summary(self) -> str:
        return self._rolling_summary

    # ------------------------------------------------------------------ #
    # Summary management
    # ------------------------------------------------------------------ #

    def _maybe_update_summary(self) -> None:
        """
        Check whether enough messages have left the short-term window
        to warrant a new rolling summary.

        The window covers messages[-SHORT_TERM_SIZE:].
        Everything before index (len - SHORT_TERM_SIZE) is eligible.
        We summarise when we have SUMMARIZE_EVERY new eligible messages.
        """
        eligible_boundary = max(0, len(self._messages) - SHORT_TERM_SIZE)
        pending = eligible_boundary - self._summarized_up_to

        if pending >= SUMMARIZE_EVERY:
            batch = self._messages[self._summarized_up_to : eligible_boundary]
            print(
                f"[MemoryManager] Updating rolling summary "
                f"(msgs {self._summarized_up_to}..{eligible_boundary})"
            )
            self._update_rolling_summary(batch)
            self._summarized_up_to = eligible_boundary
            self._save_summary()

    def _update_rolling_summary(self, new_messages: list[dict]) -> None:
        """Call the LLM to merge new_messages into the rolling summary."""
        batch_text = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}" for m in new_messages
        )
        user_content = ""
        if self._rolling_summary:
            user_content += f"Previous summary:\n{self._rolling_summary}\n\n"
        user_content += f"New messages:\n{batch_text}"

        try:
            resp = self._client.chat.completions.create(
                model=self._model_id,
                messages=[
                    {"role": "system", "content": _SUMMARY_PROMPT},
                    {"role": "user",   "content": user_content},
                ],
                temperature=0.3,
                max_tokens=300,
            )
            new_summary = resp.choices[0].message.content.strip()
            print(f"[MemoryManager] New rolling summary: {new_summary!r}")
            self._rolling_summary = new_summary
        except Exception as exc:
            print(f"[MemoryManager] Summary LLM error: {exc} — keeping old summary")

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
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT    NOT NULL,
                    role        TEXT    NOT NULL,
                    content     TEXT    NOT NULL,
                    created_at  TEXT    NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_summaries (
                    session_id        TEXT PRIMARY KEY,
                    summary           TEXT    NOT NULL DEFAULT '',
                    summarized_up_to  INTEGER NOT NULL DEFAULT 0,
                    updated_at        TEXT    NOT NULL
                )
            """)

    def _load_messages(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content FROM chat_messages "
                "WHERE session_id = ? ORDER BY id ASC",
                (self._session_id,),
            ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    def _load_summary(self) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT summary FROM chat_summaries WHERE session_id = ?",
                (self._session_id,),
            ).fetchone()
        return row["summary"] if row else ""

    def _load_summarized_up_to(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT summarized_up_to FROM chat_summaries WHERE session_id = ?",
                (self._session_id,),
            ).fetchone()
        return row["summarized_up_to"] if row else 0

    def _persist_message(self, role: str, content: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, created_at) "
                "VALUES (?, ?, ?, ?)",
                (self._session_id, role, content, now),
            )

    def _save_summary(self) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO chat_summaries (session_id, summary, summarized_up_to, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(session_id) DO UPDATE SET
                       summary          = excluded.summary,
                       summarized_up_to = excluded.summarized_up_to,
                       updated_at       = excluded.updated_at""",
                (self._session_id, self._rolling_summary, self._summarized_up_to, now),
            )
