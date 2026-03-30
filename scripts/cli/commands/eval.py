"""Evaluation commands for the CarePilot system."""

from __future__ import annotations

import subprocess
import sys
from typing import Annotated

import typer
from scripts.cli.utils import info, load_root_env

eval_app = typer.Typer(help="System evaluation and benchmarking commands.")


@eval_app.command("run")
def run_eval(
    _module: Annotated[str, typer.Option(help="Specific module to evaluate (e.g., safety).")] = "all"
) -> None:
    """Run the evaluation harness against gold standard datasets."""
    load_root_env()

    info("Starting system evaluation...")

    # Use subprocess to run the eval script to ensure clean environment and correct pathing
    cmd = [sys.executable, "scripts/evaluation/eval_harness.py"]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        info("Evaluation completed successfully.")
    else:
        typer.secho("Evaluation failed with regressions.", fg=typer.colors.RED)
        sys.exit(result.returncode)


@eval_app.callback(invoke_without_command=True)
def eval_default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        info("Use --help to see available evaluation commands.")
