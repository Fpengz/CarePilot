"""Projection replay commands for the CarePilot system."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import typer
from apps.api.carepilot_api.deps import build_app_context, close_app_context
from scripts.cli.utils import info, load_root_env

from care_pilot.platform.eventing.runner import run_projection_replay

projections_app = typer.Typer(help="Projection replay utilities.")


@projections_app.command("replay")
def replay_projections(
    user_id: Annotated[str | None, typer.Option(help="Replay only for a specific user.")] = None,
    since: Annotated[
        str | None, typer.Option(help="Replay events after ISO timestamp (e.g. 2025-01-01T00:00:00).")
    ] = None,
) -> None:
    """Replay projection handlers from the workflow timeline."""
    load_root_env()
    ctx = build_app_context()
    since_time = datetime.fromisoformat(since) if since else None
    try:
        result = run_projection_replay(
            event_timeline=ctx.event_timeline,
            eventing_store=ctx.stores.eventing,
            projection_registry=ctx.event_projections,
            coordination_store=ctx.coordination_store,
            user_id=user_id,
            since_time=since_time,
            lease_owner="projection-replay",
            lease_seconds=int(ctx.settings.storage.redis_lock_ttl_seconds),
        )
        info(
            f"Projection replay complete. applied={result.projections_applied} "
            f"skipped={result.projections_skipped}"
        )
    finally:
        close_app_context(ctx)


@projections_app.callback(invoke_without_command=True)
def projections_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        info("Use --help to see available projection commands.")
