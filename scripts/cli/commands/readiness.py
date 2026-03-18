from __future__ import annotations

import json
import os
from typing import Annotated

import typer
from scripts.cli.utils import require_cmd, run

readiness_app = typer.Typer(help="Readiness health check.")


@readiness_app.callback(invoke_without_command=True)
def readiness_default(
    ctx: typer.Context,
    base_url: Annotated[str, typer.Argument(help="API base URL")] = "http://127.0.0.1:8001",
    strict_warnings: Annotated[
        bool,
        typer.Option(
            "--strict-warnings/--no-strict-warnings",
            help="Fail on degraded status.",
        ),
    ] = False,
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    if os.environ.get("READINESS_FAIL_ON_WARNINGS", "0") == "1":
        strict_warnings = True
    require_cmd("curl")

    ready_url = f"{base_url.rstrip('/')}/api/v1/health/ready"
    payload_response = run(["curl", "-sf", ready_url], check=False, capture_output=True)
    if payload_response.returncode != 0:
        raise typer.Exit(payload_response.returncode)
    payload = payload_response.stdout

    body = json.loads(payload)
    status_value = str(body.get("status", "unknown"))
    warnings = body.get("warnings") or []
    errors = body.get("errors") or []
    typer.echo(f"readiness.status={status_value}")
    typer.echo(f"readiness.warnings={len(warnings)}")
    typer.echo(f"readiness.errors={len(errors)}")
    for item in warnings:
        typer.echo(f"warning: {item}")
    for item in errors:
        typer.echo(f"error: {item}")

    if status_value == "not_ready":
        raise typer.Exit(1)
    if status_value == "degraded" and strict_warnings:
        raise typer.Exit(1)
