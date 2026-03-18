from __future__ import annotations

import time
from typing import Annotated

import typer
from scripts.cli.utils import REPO_ROOT, error

report_app = typer.Typer(help="Generate/locate reports.")


@report_app.command("nightly")
def report_nightly(
    date_stamp: Annotated[
        str | None, typer.Argument(help="Date stamp YYYY-MM-DD.")
    ] = None,
) -> None:
    reports_dir = REPO_ROOT / "reports"
    template_path = reports_dir / "nightly_TEMPLATE.md"
    stamp = date_stamp or time.strftime("%Y-%m-%d")
    report_path = reports_dir / f"nightly_{stamp}.md"
    reports_dir.mkdir(parents=True, exist_ok=True)
    if not template_path.exists():
        error(f"Missing template: {template_path}")
        raise typer.Exit(1)
    if not report_path.exists():
        report_path.write_text(template_path.read_text())
    typer.echo(str(report_path))
