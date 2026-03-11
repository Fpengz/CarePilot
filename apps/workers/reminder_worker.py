from __future__ import annotations

import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dietary_guardian.application.reminders.service import ReminderService
from dietary_guardian.infrastructure.reminders.delivery import build_delivery_adapter
from dietary_guardian.infrastructure.reminders.knowledge import (
    EmptyDrugKnowledgeRepository,
    JsonDrugKnowledgeRepository,
)
from dietary_guardian.infrastructure.reminders.outbox_sqlite import SQLiteOutboxRepository
from dietary_guardian.infrastructure.reminders.repository import SQLiteReminderRepository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(slots=True, frozen=True)
class ReminderWorkerConfig:
    db_path: str
    drug_knowledge_dir: str
    channel: str
    poll_interval_seconds: int
    batch_size: int
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_dev_mode: bool
    log_level: str
    use_empty_knowledge_fallback: bool

    @classmethod
    def from_env(cls) -> "ReminderWorkerConfig":
        base_data_dir = os.getenv("DATA_DIR", "data")

        db_path = os.getenv(
            "REMINDER_DB_PATH",
            str(Path(base_data_dir) / "reminders.db"),
        )
        drug_knowledge_dir = os.getenv(
            "REMINDER_KNOWLEDGE_DIR",
            str(Path(base_data_dir) / "drug_knowledge"),
        )

        return cls(
            db_path=db_path,
            drug_knowledge_dir=drug_knowledge_dir,
            channel=os.getenv("REMINDER_DEFAULT_CHANNEL", "telegram"),
            poll_interval_seconds=_env_int("REMINDER_WORKER_POLL_INTERVAL_SECONDS", 15),
            batch_size=_env_int("REMINDER_WORKER_BATCH_SIZE", 50),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            telegram_dev_mode=_env_bool("TELEGRAM_DEV_MODE", True),
            log_level=os.getenv("REMINDER_WORKER_LOG_LEVEL", "INFO"),
            use_empty_knowledge_fallback=_env_bool("REMINDER_USE_EMPTY_KNOWLEDGE_FALLBACK", True),
        )


# ---------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------


def setup_logging(level: str = "INFO") -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def build_knowledge_repository(config: ReminderWorkerConfig):
    knowledge_dir = Path(config.drug_knowledge_dir)

    if knowledge_dir.exists() and knowledge_dir.is_dir():
        logger.info("Using JsonDrugKnowledgeRepository at %s", knowledge_dir)
        return JsonDrugKnowledgeRepository(knowledge_dir)

    if config.use_empty_knowledge_fallback:
        logger.warning(
            "Drug knowledge directory not found: %s. Falling back to EmptyDrugKnowledgeRepository.",
            knowledge_dir,
        )
        return EmptyDrugKnowledgeRepository()

    raise FileNotFoundError(
        f"Drug knowledge directory does not exist: {knowledge_dir}"
    )


def build_service(config: ReminderWorkerConfig) -> ReminderService:
    repo = SQLiteReminderRepository(config.db_path)
    outbox = SQLiteOutboxRepository(config.db_path)

    delivery = build_delivery_adapter(
        channel=config.channel,
        telegram_bot_token=config.telegram_bot_token,
        telegram_chat_id=config.telegram_chat_id,
        telegram_dev_mode=config.telegram_dev_mode,
        fallback_to_mock=True,
    )

    knowledge = build_knowledge_repository(config)

    service = ReminderService(
        reminder_repo=repo,
        outbox_repo=outbox,
        metric_repo=repo,
        food_repo=repo,
        delivery=delivery,
        drug_knowledge=knowledge,
        default_channel=config.channel,
    )
    return service


# ---------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------


class ReminderWorker:
    """
    Reminder outbox worker.

    Responsibilities:
    1. Bootstrap reminder service with SQLite repositories and delivery adapter
    2. Pull due events from outbox
    3. Dispatch them through delivery port
    4. Update outbox/reminder states via ReminderService
    """

    def __init__(self, config: Optional[ReminderWorkerConfig] = None) -> None:
        self.config = config or ReminderWorkerConfig.from_env()
        self._running = False
        self.service = build_service(self.config)

    def run_once(self) -> int:
        logger.info(
            "Reminder worker tick started | db=%s | channel=%s | batch_size=%s",
            self.config.db_path,
            self.config.channel,
            self.config.batch_size,
        )

        results = self.service.dispatch_due_events(limit=self.config.batch_size)

        total = len(results)
        success_count = sum(1 for r in results if r.success)
        failed_count = total - success_count

        logger.info(
            "Reminder worker tick finished | total=%s | success=%s | failed=%s",
            total,
            success_count,
            failed_count,
        )

        for idx, result in enumerate(results, start=1):
            if result.success:
                logger.debug(
                    "Dispatch result #%s | success | provider_msg_id=%s",
                    idx,
                    result.provider_msg_id,
                )
            else:
                logger.warning(
                    "Dispatch result #%s | failed | error=%s",
                    idx,
                    result.error,
                )

        return total

    def run_forever(self) -> None:
        self._running = True
        logger.info(
            "Reminder worker started | poll_interval_seconds=%s",
            self.config.poll_interval_seconds,
        )

        while self._running:
            try:
                self.run_once()
            except Exception as exc:
                logger.exception("Reminder worker tick failed: %s", exc)

            time.sleep(self.config.poll_interval_seconds)

        logger.info("Reminder worker stopped.")

    def stop(self) -> None:
        logger.info("Stop signal received by reminder worker.")
        self._running = False


# ---------------------------------------------------------------------
# Signal handling
# ---------------------------------------------------------------------


def _install_signal_handlers(worker: ReminderWorker) -> None:
    def _handle_signal(signum, frame) -> None:  # noqa: ARG001
        logger.info("Received signal: %s", signum)
        worker.stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)


# ---------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------


def run_once() -> int:
    config = ReminderWorkerConfig.from_env()
    setup_logging(config.log_level)
    worker = ReminderWorker(config)
    return worker.run_once()


def run_forever() -> None:
    config = ReminderWorkerConfig.from_env()
    setup_logging(config.log_level)
    worker = ReminderWorker(config)
    _install_signal_handlers(worker)
    worker.run_forever()


# ---------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------


def main() -> int:
    config = ReminderWorkerConfig.from_env()
    setup_logging(config.log_level)

    mode = os.getenv("REMINDER_WORKER_MODE", "once").strip().lower()
    worker = ReminderWorker(config)

    if mode == "once":
        worker.run_once()
        return 0

    if mode == "forever":
        _install_signal_handlers(worker)
        worker.run_forever()
        return 0

    logger.error(
        "Invalid REMINDER_WORKER_MODE=%s. Expected 'once' or 'forever'.",
        mode,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())