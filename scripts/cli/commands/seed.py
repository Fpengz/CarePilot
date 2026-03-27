from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Annotated, cast

import typer
from scripts.cli.commands.ingest import _resolve_app_db_path
from scripts.cli.utils import REPO_ROOT, error, load_root_env

from care_pilot.dev.synthetic_data import SyntheticProfile, seed_demo_accounts, seed_synthetic_data

seed_app = typer.Typer(help="Seed developer synthetic data.")


@seed_app.command("accounts")
def seed_accounts(
    auth_db: Annotated[
        str | None,
        typer.Option(
            "--auth-db",
            help="Optional auth DB path (default: data/care_pilot_auth.db).",
        ),
    ] = None,
    app_db: Annotated[
        str | None,
        typer.Option(
            "--app-db",
            help="Optional application DB path (default: data/care_pilot_api.db).",
        ),
    ] = None,
    accounts_file: Annotated[
        str | None,
        typer.Option(
            "--accounts-file",
            help="JSON file with account seeds (default: data/seeds/demo_accounts.json).",
        ),
    ] = None,
    profiles_file: Annotated[
        str | None,
        typer.Option(
            "--profiles-file",
            help="JSON file with profile seeds (default: data/seeds/demo_profiles.json).",
        ),
    ] = None,
) -> None:
    """Seed standard demo accounts and their initial health profiles."""
    load_root_env()
    from care_pilot.config import get_settings

    settings = get_settings()
    resolved_auth_db = auth_db or settings.auth.sqlite_db_path
    resolved_app_db = app_db or settings.storage.api_sqlite_db_path
    resolved_accounts_file = Path(accounts_file or REPO_ROOT / "data/seeds/demo_accounts.json")
    resolved_profiles_file = Path(profiles_file or REPO_ROOT / "data/seeds/demo_profiles.json")

    if not resolved_accounts_file.exists():
        error(f"Accounts file not found: {resolved_accounts_file}")
        raise typer.Exit(1)
    if not resolved_profiles_file.exists():
        error(f"Profiles file not found: {resolved_profiles_file}")
        raise typer.Exit(1)

    with open(resolved_accounts_file) as f:
        accounts = json.load(f)
    with open(resolved_profiles_file) as f:
        profiles = json.load(f)

    seed_demo_accounts(
        auth_db_path=resolved_auth_db,
        app_db_path=resolved_app_db,
        accounts=accounts,
        profiles=profiles,
    )
    typer.echo(f"Demo accounts and profiles seeded in {resolved_auth_db} and {resolved_app_db}")


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
