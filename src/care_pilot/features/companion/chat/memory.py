"""
Manage chat memory for the companion agent.

This module persists long-term chat history, maintains a short-term window,
and builds prompt context for the chat agent runtime.
"""

from __future__ import annotations

import asyncio
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

from care_pilot.agent.chat.schemas import ChatSummaryOutput
from care_pilot.agent.runtime.inference_types import (
    InferenceModality,
    InferenceRequest,
)
from care_pilot.platform.observability import get_logger

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SHORT_TERM_SIZE = 3  # messages kept in the prompt window
SUMMARIZE_EVERY = 3  # trigger summarisation after N new out-of-window msgs
# User-scoped history uses a fixed session id to keep the schema unchanged.
USER_HISTORY_SESSION_ID = "user"

BASE_DIR = Path(__file__).resolve().parents[4]
DB_PATH = BASE_DIR / "data" / "runtime" / "chat_memory.db"

_SUMMARY_PROMPT = """\
You are a conversation summarizer. Given the previous rolling summary and a \
batch of new messages, produce a concise updated summary that captures the \
key topics, facts, and decisions discussed. Do not include greetings or filler. \
Write in third-person ("The user asked…", "The assistant explained…"). \
Return the summary in the `summary` field only.
"""


# ---------------------------------------------------------------------------
# MemoryManager
# ---------------------------------------------------------------------------


class InferenceEngineProtocol(Protocol):
    async def infer(self, request: InferenceRequest): ...  # noqa: ANN001


class MemoryManager:
    """
    Maintains long-term chat history in SQLite and a short-term window
    (latest SHORT_TERM_SIZE messages) in memory.

    After every SUMMARIZE_EVERY messages leave the short-term window,
    the LLM is called to update the rolling summary.
    """

    def __init__(
        self,
        user_id: str,
        session_id: str,
        inference_engine: InferenceEngineProtocol,
        db_path: Path = DB_PATH,
    ) -> None:
        self._user_id = user_id
        # Persist history per user, not per session.
        self._session_id = USER_HISTORY_SESSION_ID
        self._engine = inference_engine
        self._db_path = db_path
        self._logger = get_logger(__name__)

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

        # Load persisted state
        self._messages: list[dict] = self._load_messages()
        self._rolling_summary: str = self._load_summary()
        self._summarized_up_to: int = self._load_summarized_up_to()
        self._summary_in_flight = False

        self._logger.info(
            "chat_memory_ready user_id=%s session=%s messages=%s summarized_up_to=%s",
            user_id,
            self._session_id,
            len(self._messages),
            self._summarized_up_to,
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
            "short_term": self._messages[-SHORT_TERM_SIZE:],
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
            if self._summary_in_flight:
                return
            batch = self._messages[self._summarized_up_to : eligible_boundary]
            self._logger.info(
                "chat_memory_summary_update msgs_start=%s msgs_end=%s",
                self._summarized_up_to,
                eligible_boundary,
            )
            self._summary_in_flight = True
            self._schedule_summary_update(batch, eligible_boundary)

    def _schedule_summary_update(self, new_messages: list[dict], eligible_boundary: int) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._update_and_persist_summary(new_messages, eligible_boundary))
            return

        loop.create_task(self._update_and_persist_summary(new_messages, eligible_boundary))

    async def _update_and_persist_summary(
        self, new_messages: list[dict], eligible_boundary: int
    ) -> None:
        try:
            await self._update_rolling_summary(new_messages)
        finally:
            self._summarized_up_to = eligible_boundary
            self._save_summary()
            self._summary_in_flight = False

    async def _update_rolling_summary(self, new_messages: list[dict]) -> None:
        """Call the LLM to merge new_messages into the rolling summary."""
        batch_text = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in new_messages)
        user_content = ""
        if self._rolling_summary:
            user_content += f"Previous summary:\n{self._rolling_summary}\n\n"
        user_content += f"New messages:\n{batch_text}"

        try:
            request = InferenceRequest(
                request_id=str(uuid.uuid4()),
                user_id=self._user_id,
                modality=InferenceModality.TEXT,
                payload={"prompt": user_content},
                output_schema=ChatSummaryOutput,
                system_prompt=_SUMMARY_PROMPT,
            )
            response = await self._engine.infer(request)
            output = cast(ChatSummaryOutput, response.structured_output)
            new_summary = output.summary.strip()
            self._rolling_summary = new_summary
            self._logger.info("chat_memory_summary_updated length=%s", len(new_summary))
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("chat_memory_summary_failed error=%s", exc)

    # ------------------------------------------------------------------ #
    # SQLite helpers
    # ------------------------------------------------------------------ #

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            if not _table_has_column(conn, "chat_messages", "user_id"):
                conn.execute("DROP TABLE IF EXISTS chat_messages")
            if not _table_has_column(conn, "chat_summaries", "user_id"):
                conn.execute("DROP TABLE IF EXISTS chat_summaries")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     TEXT    NOT NULL,
                    session_id  TEXT    NOT NULL,
                    role        TEXT    NOT NULL,
                    content     TEXT    NOT NULL,
                    created_at  TEXT    NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_summaries (
                    user_id          TEXT    NOT NULL,
                    session_id       TEXT    NOT NULL,
                    summary          TEXT    NOT NULL DEFAULT '',
                    summarized_up_to INTEGER NOT NULL DEFAULT 0,
                    updated_at       TEXT    NOT NULL,
                    PRIMARY KEY (user_id, session_id)
                )
            """)

    def _load_messages(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content FROM chat_messages "
                "WHERE user_id = ? AND session_id = ? ORDER BY id ASC",
                (self._user_id, self._session_id),
            ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    def _load_summary(self) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT summary FROM chat_summaries WHERE user_id = ? AND session_id = ?",
                (self._user_id, self._session_id),
            ).fetchone()
        return row["summary"] if row else ""

    def _load_summarized_up_to(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT summarized_up_to FROM chat_summaries WHERE user_id = ? AND session_id = ?",
                (self._user_id, self._session_id),
            ).fetchone()
        return row["summarized_up_to"] if row else 0

    def _persist_message(self, role: str, content: str) -> None:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO chat_messages (user_id, session_id, role, content, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (self._user_id, self._session_id, role, content, now),
            )

    def _save_summary(self) -> None:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO chat_summaries (user_id, session_id, summary, summarized_up_to, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, session_id) DO UPDATE SET
                       summary          = excluded.summary,
                       summarized_up_to = excluded.summarized_up_to,
                       updated_at       = excluded.updated_at""",
                (
                    self._user_id,
                    self._session_id,
                    self._rolling_summary,
                    self._summarized_up_to,
                    now,
                ),
            )


def _table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)
