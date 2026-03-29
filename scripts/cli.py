#!/usr/bin/env python3
"""Developer CLI for the current CarePilot backend, web, and infra workflows.

Modularized version of the CLI.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add the project root to sys.path so that 'scripts' can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import typer
from scripts.cli.commands.dev import dev_app
from scripts.cli.commands.eval import eval_app
from scripts.cli.commands.infra import infra_app
from scripts.cli.commands.ingest import ingest_app
from scripts.cli.commands.maintenance import maintenance_app
from scripts.cli.commands.projections import projections_app
from scripts.cli.commands.readiness import readiness_app
from scripts.cli.commands.reminder import reminder_app
from scripts.cli.commands.report import report_app
from scripts.cli.commands.seed import seed_app
from scripts.cli.commands.test import test_app
from scripts.cli.commands.web import web_app as web_app_impl

app = typer.Typer(help="CarePilot unified developer CLI.")

app.add_typer(dev_app, name="dev")
app.add_typer(eval_app, name="eval")
app.add_typer(infra_app, name="infra")
app.add_typer(maintenance_app, name="maintenance")
app.add_typer(test_app, name="test")
app.add_typer(report_app, name="report")
app.add_typer(web_app := typer.Typer(help="Web helper commands."), name="web")
app.add_typer(ingest_app, name="ingest")
app.add_typer(seed_app, name="seed")
app.add_typer(reminder_app, name="reminders")
app.add_typer(readiness_app, name="readiness")
app.add_typer(projections_app, name="projections")

web_app.add_typer(web_app_impl, name="env")



@app.command("help")
def help_command() -> None:
    typer.echo(
        "\n".join(
            [
                "Usage:",
                "  uv run python scripts/cli.py dev [--no-api] [--no-web] [--no-scheduler]",
                "  uv run python scripts/cli.py infra [up|down|restart|status|logs]",
                "  uv run python scripts/cli.py maintenance prune-events [--days 90]",
                "  uv run python scripts/cli.py readiness [base_url] [--strict-warnings]",
                "  uv run python scripts/cli.py test [backend|web|comprehensive] [--skip-e2e] [--skip-smoke] [--no-infra-bootstrap]",
                "  uv run python scripts/cli.py ingest local",
                "  uv run python scripts/cli.py ingest canonical [--reset]",
                "  uv run python scripts/cli.py ingest usda <path> [--reset]",
                "  uv run python scripts/cli.py ingest off <path> [--reset]",
                "  uv run python scripts/cli.py report nightly [date]",
                "  uv run python scripts/cli.py projections replay [--user-id USER] [--since ISO]",
                "  uv run python scripts/cli.py web env -- <command...>",
                "  uv run python scripts/cli.py help",
            ]
        )
    )


def main() -> None:
    if len(sys.argv) == 1:
        app(["help"], standalone_mode=False)
        return
    app()


if __name__ == "__main__":
    main()
