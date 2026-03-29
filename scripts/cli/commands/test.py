from __future__ import annotations

from typing import Annotated

import typer
from scripts.cli.utils import assert_no_extra_args, info, require_cmd, run_step

test_app = typer.Typer(help="Run validation suites.")


def execute_test_backend() -> None:
    require_cmd("uv")
    run_step("ruff", ["uv", "run", "ruff", "check", "."])
    run_step(
        "ty",
        [
            "uv",
            "run",
            "ty",
            "check",
            ".",
            "--extra-search-path",
            "src",
            "--output-format",
            "concise",
        ],
    )
    run_step("pytest", ["uv", "run", "pytest", "-q"])


@test_app.command(
    "backend",
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
)
def test_backend(ctx: typer.Context) -> None:
    assert_no_extra_args(ctx.args, "Usage: uv run python scripts/cli.py test backend")
    execute_test_backend()


@test_app.command("web")
def test_web(
    skip_e2e: Annotated[bool, typer.Option("--skip-e2e", help="Skip end-to-end tests.")] = False,
) -> None:
    require_cmd("pnpm")
    run_step("web:lint", ["pnpm", "--dir", "apps/web", "lint"])
    run_step("web:typecheck", ["pnpm", "--dir", "apps/web", "typecheck"])
    run_step("web:build", ["pnpm", "--dir", "apps/web", "build"])
    if skip_e2e:
        info("Skipping web:e2e (--skip-e2e)")
    else:
        run_step("web:e2e", ["pnpm", "--dir", "apps/web", "test:e2e"])


@test_app.command("comprehensive")
def test_comprehensive(
    skip_e2e: Annotated[bool, typer.Option("--skip-e2e", help="Skip web e2e tests.")] = False,
    skip_smoke: Annotated[
        bool,
        typer.Option("--skip-smoke", help="Skip legacy shared-topology smoke flow."),
    ] = False,
    no_infra_bootstrap: Annotated[
        bool,
        typer.Option("--no-infra-bootstrap", help="Skip infra bootstrap in smoke flow."),
    ] = False,
) -> None:
    execute_test_backend()
    test_web(skip_e2e=skip_e2e)
    if skip_smoke:
        info("Skipping removed shared-topology smoke (--skip-smoke)")
        return

    if no_infra_bootstrap:
        info("Ignoring --no-infra-bootstrap in the SQLite-first runtime.")
