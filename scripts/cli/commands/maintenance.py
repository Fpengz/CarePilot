"""Maintenance commands for the CarePilot system."""

from __future__ import annotations

from typing import Annotated

import typer
from scripts.cli.utils import info, load_root_env

from care_pilot.config.app import get_settings
from care_pilot.platform.persistence.maintenance import backup_sqlite_db, rotate_backups
from care_pilot.platform.persistence.sqlite_repository import SQLiteRepository

maintenance_app = typer.Typer(help="System maintenance and cleanup commands.")


@maintenance_app.command("backup-db")
def backup_db(
    backup_dir: Annotated[str, typer.Option(help="Directory to store backups.")] = "data/backups",
    keep: Annotated[int, typer.Option(help="Number of backups to keep.")] = 7,
) -> None:
    """Create a consistent backup of the SQLite database."""
    load_root_env()
    settings = get_settings()
    db_path = settings.storage.api_sqlite_db_path

    info(f"Backing up database {db_path} to {backup_dir}...")
    backup_path = backup_sqlite_db(db_path, backup_dir)
    rotate_backups(backup_dir, keep_count=keep)

    info(f"Successfully created backup: {backup_path}")


@maintenance_app.command("prune-events")
def prune_events(
    days: Annotated[int, typer.Option(help="Prune events older than N days.")] = 90
) -> None:
    """Prune stale workflow timeline events from the database."""
    load_root_env()
    settings = get_settings()
    db_path = settings.storage.api_sqlite_db_path

    info(f"Pruning workflow events older than {days} days from {db_path}...")

    repo = SQLiteRepository(db_path)
    count = repo.prune_events(days=days)

    info(f"Successfully pruned {count} events.")


@maintenance_app.callback(invoke_without_command=True)
def maintenance_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        info("Use --help to see available maintenance commands.")
