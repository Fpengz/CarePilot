"""Maintenance commands for the CarePilot system."""

from __future__ import annotations

from typing import Annotated

import typer
from scripts.cli.utils import info, load_root_env

from care_pilot.config.app import get_settings
from care_pilot.platform.persistence.sqlite_repository import SQLiteRepository

maintenance_app = typer.Typer(help="System maintenance and cleanup commands.")


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
