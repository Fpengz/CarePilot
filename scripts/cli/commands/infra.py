from __future__ import annotations

import shutil
from typing import Annotated

import typer
from scripts.cli.utils import (
    COMPOSE_FILE,
    REDIS_CONTAINER,
    REDIS_IMAGE,
    REDIS_VOLUME,
    error,
    info,
    require_cmd,
    run,
    wait_for_tcp,
    warning,
)

infra_app = typer.Typer(help="Manage local infra (Redis).")


def compose_available() -> bool:
    return run(["docker", "compose", "version"], check=False).returncode == 0


def docker_compose_available() -> bool:
    return shutil.which("docker-compose") is not None


def infra_backend_name() -> str:
    if compose_available() or docker_compose_available():
        return "compose"
    return "docker-run fallback"


def ensure_docker_daemon() -> None:
    require_cmd("docker")
    if run(["docker", "info"], check=False).returncode != 0:
        error(
            "Docker daemon is not running. Start Docker Desktop/daemon and retry. "
            "For non-Docker environments, run: uv run python scripts/cli.py test comprehensive --skip-smoke"
        )
        raise typer.Exit(1)


def infra_compose(args: list[str]) -> int:
    if compose_available():
        return run(
            ["docker", "compose", "-f", str(COMPOSE_FILE), *args], check=False
        ).returncode
    if docker_compose_available():
        return run(
            ["docker-compose", "-f", str(COMPOSE_FILE), *args], check=False
        ).returncode
    warning("Compose is unavailable; falling back to plain docker runtime.")
    return 125


def docker_runtime_up() -> None:
    run(["docker", "volume", "create", REDIS_VOLUME], check=True)

    existing = run(
        ["docker", "ps", "-a", "--format", "{{.Names}}"],
        check=True,
        capture_output=True,
    ).stdout
    names = set(existing.splitlines())

    if REDIS_CONTAINER not in names:
        run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                REDIS_CONTAINER,
                "--restart",
                "unless-stopped",
                "-p",
                "6379:6379",
                "-v",
                f"{REDIS_VOLUME}:/data",
                REDIS_IMAGE,
            ],
            check=True,
        )
    else:
        run(["docker", "start", REDIS_CONTAINER], check=False)


def docker_runtime_down() -> None:
    run(["docker", "rm", "-f", REDIS_CONTAINER], check=False)


def docker_runtime_status() -> None:
    run(
        [
            "docker",
            "ps",
            f"name=^{REDIS_CONTAINER}$",
            "--format",
            "table {{.Names}}\t{{.Status}}\t{{.Ports}}",
        ],
        check=True,
    )


def docker_runtime_logs() -> None:
    run(["docker", "logs", "--tail", "200", REDIS_CONTAINER], check=False)


def infra_run(command: str, extra_args: list[str] | None = None) -> None:
    args = extra_args or []
    if compose_available() or docker_compose_available():
        code = infra_compose([command, *args])
        if code != 0:
            raise typer.Exit(code)
        return
    if command == "up":
        docker_runtime_up()
        return
    if command == "down":
        docker_runtime_down()
        return
    if command == "ps":
        docker_runtime_status()
        return
    if command == "logs":
        docker_runtime_logs()
        return
    error(f"Unsupported infra backend command: {command}")
    raise typer.Exit(2)


@infra_app.callback(invoke_without_command=True)
def infra_default(
    ctx: typer.Context,
    action: Annotated[
        str,
        typer.Argument(
            help="Action: up/down/restart/status/logs",
            metavar="[up|down|restart|status|logs]",
        ),
    ] = "up",
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    if action not in {"up", "down", "restart", "status", "logs"}:
        error(f"Unknown infra subcommand: {action}")
        raise typer.Exit(2)

    require_cmd("uv")
    ensure_docker_daemon()

    if action == "up":
        infra_run("up", ["-d", "redis"])
        if not wait_for_tcp("127.0.0.1", 6379, timeout_seconds=60):
            error("Redis did not become reachable on 127.0.0.1:6379 within timeout.")
            raise typer.Exit(1)
        info(f"Infra is ready (backend: {infra_backend_name()})")
        infra_run("ps")
        return
    if action == "down":
        infra_run("down")
        return
    if action == "restart":
        infra_run("down")
        infra_run("up", ["-d", "redis"])
        info(f"Infra backend: {infra_backend_name()}")
        infra_run("ps")
        return
    if action == "status":
        info(f"Infra backend: {infra_backend_name()}")
        infra_run("ps")
        return
    info(f"Infra backend: {infra_backend_name()}")
    infra_run("logs", ["--tail=200", "redis"])
