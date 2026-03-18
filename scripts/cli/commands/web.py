from __future__ import annotations

import os

import typer
from scripts.cli.utils import error, load_root_env, load_web_env, run

web_app = typer.Typer(help="Web helper commands.")


@web_app.command(
    "env",
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
)
def web_env(ctx: typer.Context) -> None:
    args = list(ctx.args)
    if args and args[0] == "--":
        args = args[1:]
    if not args:
        error("web env requires '--' followed by command to execute")
        raise typer.Exit(2)
    load_root_env()
    load_web_env()
    code = run(args, check=False, env=os.environ.copy()).returncode
    if code != 0:
        raise typer.Exit(code)
