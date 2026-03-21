from __future__ import annotations

import sqlite3
import sys
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

import typer
from scripts.cli.utils import (
    REPO_ROOT,
    error,
    info,
    load_root_env,
)

from care_pilot.config.app import get_settings
from care_pilot.features.reminders.domain.models import ReminderEvent
from care_pilot.platform.messaging.channels.telegram import TelegramChannel
from care_pilot.platform.persistence.sqlite_db import get_connection

reminder_app = typer.Typer(help="Reminder and notification commands.")


@reminder_app.command("dispatch")
def command_reminders_dispatch() -> None:
    """Dispatch due reminder notifications once (scheduler + outbox)."""
    load_root_env()
    import asyncio

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from care_pilot.platform.scheduling import run_reminder_scheduler_once

    result = asyncio.run(run_reminder_scheduler_once())
    info(
        f"reminders.dispatch queued={result.queued_count} deliveries={result.delivery_attempts}"
    )


@reminder_app.command("diagnose")
def command_reminders_diagnose(
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            help="How many recent scheduled notifications to inspect.",
        ),
    ] = 10,
) -> None:
    """Show a compact reminder delivery pipeline snapshot."""
    load_root_env()
    settings = get_settings()
    db_path = settings.storage.api_sqlite_db_path

    def _mask_token(value: str | None) -> str:
        if not value:
            return "missing"
        return f"***{value[-4:]}" if len(value) >= 4 else "***"

    typer.echo(f"db_path={db_path}")
    typer.echo(
        "telegram_config token={} chat_id={} dev_mode={}".format(
            _mask_token(settings.channels.telegram_bot_token),
            "present" if settings.channels.telegram_chat_id else "missing",
            settings.channels.telegram_dev_mode,
        )
    )

    try:
        conn = get_connection(db_path)
    except sqlite3.Error as exc:
        error(f"Failed to open db: {exc}")
        raise typer.Exit(1) from exc

    with conn:
        cur = conn.cursor()

        typer.echo("scheduled_notifications_status_counts:")
        try:
            rows = cur.execute(
                "SELECT status, COUNT(*) FROM scheduled_notifications GROUP BY status ORDER BY status"
            ).fetchall()
            if not rows:
                typer.echo("  (none)")
            for status, count in rows:
                typer.echo(f"  {status}: {count}")
        except sqlite3.Error as exc:
            typer.echo(f"  error: {exc}")

        typer.echo("alert_outbox_state_counts:")
        try:
            rows = cur.execute(
                "SELECT state, sink, COUNT(*) FROM alert_outbox GROUP BY state, sink ORDER BY state, sink"
            ).fetchall()
            if not rows:
                typer.echo("  (none)")
            for state, sink, count in rows:
                typer.echo(f"  {state} | {sink}: {count}")
        except sqlite3.Error as exc:
            typer.echo(f"  error: {exc}")

        typer.echo("notification_logs_recent:")
        try:
            recent_ids = cur.execute(
                "SELECT id FROM scheduled_notifications ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            ids = [row[0] for row in recent_ids]
            if not ids:
                typer.echo("  (none)")
            else:
                placeholders = ",".join("?" for _ in ids)
                query = (
                    "SELECT scheduled_notification_id, event_type, COUNT(*) "
                    "FROM notification_logs "
                    f"WHERE scheduled_notification_id IN ({placeholders}) "
                    "GROUP BY scheduled_notification_id, event_type "
                    "ORDER BY scheduled_notification_id, event_type"
                )
                rows = cur.execute(query, ids).fetchall()
                if not rows:
                    typer.echo("  (none)")
                for scheduled_id, event_type, count in rows:
                    typer.echo(f"  {scheduled_id} | {event_type}: {count}")
        except sqlite3.Error as exc:
            typer.echo(f"  error: {exc}")


@reminder_app.command("telegram-test")
def command_telegram_test(
    message: Annotated[
        str,
        typer.Option("--message", "-m", help="Text to include in the reminder payload."),
    ] = "Test reminder",
    bot_token: Annotated[
        str | None,
        typer.Option("--bot-token", help="Override TELEGRAM_BOT_TOKEN."),
    ] = None,
    chat_id: Annotated[
        str | None,
        typer.Option("--chat-id", help="Override TELEGRAM_CHAT_ID."),
    ] = None,
    dev_mode: Annotated[
        bool | None,
        typer.Option("--dev-mode/--no-dev-mode", help="Override TELEGRAM_DEV_MODE."),
    ] = None,
) -> None:
    load_root_env()
    settings = get_settings()
    token = bot_token or settings.channels.telegram_bot_token or ""
    destination = chat_id or settings.channels.telegram_chat_id or ""
    use_dev_mode = settings.channels.telegram_dev_mode if dev_mode is None else dev_mode

    if not token or not destination:
        error(
            "Missing Telegram configuration. Provide --bot-token and --chat-id or set TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID."
        )
        raise typer.Exit(1)

    channel = TelegramChannel()
    channel.bot_token = token
    channel.chat_id = destination
    channel.dev_mode = use_dev_mode

    reminder = ReminderEvent(
        id=str(uuid4()),
        user_id="cli",
        reminder_definition_id=None,
        occurrence_id=None,
        regimen_id=None,
        reminder_type="medication",
        title="Telegram test reminder",
        body=message,
        medication_name=message,
        scheduled_at=datetime.now(UTC),
        slot=None,
        dosage_text="",
        status="sent",
        meal_confirmation="unknown",
        sent_at=None,
        ack_at=None,
    )
    result = channel.send(reminder, destination=f"telegram://{destination}")
    if result.success:
        info("Telegram test dispatched successfully.")
        return
    error(f"Telegram test failed: {result.error or 'unknown error'}")
    raise typer.Exit(1)
