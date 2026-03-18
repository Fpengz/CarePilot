from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated, cast

import typer
from scripts.cli.commands.ingest import _resolve_app_db_path
from scripts.cli.utils import REPO_ROOT, error, load_root_env

from care_pilot.dev.synthetic_data import SyntheticProfile, seed_synthetic_data

seed_app = typer.Typer(help="Seed developer synthetic data.")

@seed_app.command("synthetic")
def seed_synthetic(
    user_id: Annotated[str, typer.Option("--user-id", help="Target user ID to seed.")] = "user_001",
    days: Annotated[int, typer.Option("--days", min=1, help="Number of days to generate.")] = 90,
    seed: Annotated[int, typer.Option("--seed", help="Deterministic random seed.")] = 17,
    profile: Annotated[
        str,
        typer.Option(
            "--profile",
            help="Pattern profile: stable, improving, or volatile.",
        ),
    ] = "stable",
    start_date: Annotated[
        str | None,
        typer.Option("--start-date", help="Optional inclusive start date (YYYY-MM-DD)."),
    ] = None,
    reset: Annotated[
        bool,
        typer.Option("--reset", help="Delete existing target-user data before seeding."),
    ] = False,
    append: Annotated[
        bool,
        typer.Option(
            "--append",
            help="Append synthetic data after the latest generated day.",
        ),
    ] = False,
    chat_db: Annotated[
        str | None,
        typer.Option(
            "--chat-db",
            help="Optional chat memory DB path for BP tracking (default: data/runtime/chat_memory.db).",
        ),
    ] = None,
) -> None:
    load_root_env()
    if reset == append:
        error("choose exactly one of --reset or --append")
        raise typer.Exit(2)

    if profile not in {"stable", "improving", "volatile"}:
        error("profile must be one of: stable, improving, volatile")
        raise typer.Exit(2)
    parsed_start_date: date | None = None
    if start_date:
        try:
            parsed_start_date = date.fromisoformat(start_date)
        except ValueError:
            error("start-date must use YYYY-MM-DD")
            raise typer.Exit(2) from None

    resolved_chat_db = chat_db or str(REPO_ROOT / "data" / "runtime" / "chat_memory.db")
    if resolved_chat_db:
        Path(resolved_chat_db).expanduser().parent.mkdir(parents=True, exist_ok=True)
    summary = seed_synthetic_data(
        db_path=_resolve_app_db_path(),
        user_id=user_id,
        days=days,
        seed=seed,
        profile=cast(SyntheticProfile, profile),
        reset=reset,
        append=append,
        start_date=parsed_start_date,
        chat_db_path=resolved_chat_db,
    )
    typer.echo("seed.synthetic.complete")
    typer.echo(f"db_path={summary.db_path}")
    typer.echo(f"user_id={summary.user_id}")
    typer.echo(f"date_range={summary.start_date.isoformat()}..{summary.end_date.isoformat()}")
    typer.echo(f"meals={summary.meals}")
    typer.echo(f"nutrition_profiles={summary.nutrition_profiles}")
    typer.echo(f"biomarkers={summary.biomarkers}")
    typer.echo(f"adherence_events={summary.adherence_events}")
    typer.echo(f"reminders={summary.reminders}")
    typer.echo(f"regimens={summary.regimens}")
    typer.echo(f"chat_bp_readings={summary.chat_bp_readings}")
