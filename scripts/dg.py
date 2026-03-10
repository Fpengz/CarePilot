#!/usr/bin/env python3
"""Developer CLI for the current Dietary Guardian backend, web, and infra workflows.

This script is the canonical entry point for local development tasks in the
modular monolith: starting the API and web surfaces, bootstrapping Redis-backed
ephemeral state when needed, running validation suites, and locating generated
reports. The command set mirrors the current repository layout under `apps/`,
`src/`, and `reports/` rather than older legacy runtime shapes.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Annotated

import typer
from dotenv import dotenv_values

app = typer.Typer(help="Dietary Guardian unified developer CLI.")
infra_app = typer.Typer(help="Manage local infra (Redis).")
migrate_app = typer.Typer(help="Migration helpers.")
test_app = typer.Typer(help="Run validation suites.")
report_app = typer.Typer(help="Generate/locate reports.")
web_app = typer.Typer(help="Web helper commands.")

app.add_typer(infra_app, name="infra")
app.add_typer(migrate_app, name="migrate")
app.add_typer(test_app, name="test")
app.add_typer(report_app, name="report")
app.add_typer(web_app, name="web")

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPO_ROOT / "compose.dev.yml"
REDIS_CONTAINER = "dietary_guardian_dev_redis"
REDIS_VOLUME = "dietary_guardian_dev_redis_data"
REDIS_IMAGE = "redis:7-alpine"


def info(message: str) -> None:
    typer.echo(f"[dg] {message}")


def warning(message: str) -> None:
    typer.echo(f"[dg] warning: {message}", err=True)


def error(message: str) -> None:
    typer.echo(f"[dg] error: {message}", err=True)


def require_cmd(command: str) -> None:
    if shutil.which(command) is None:
        error(f"Missing dependency: {command}")
        raise typer.Exit(127)


def load_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    for key, value in dotenv_values(env_path).items():
        if value is not None and key not in os.environ:
            os.environ[key] = value


def load_root_env() -> None:
    load_env(REPO_ROOT / ".env")


def load_web_env() -> None:
    load_env(REPO_ROOT / "apps" / "web" / ".env")


def run(
    args: list[str],
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        check=check,
        env=env,
        text=True,
        capture_output=capture_output,
    )


def wait_for_tcp(host: str, port: int, timeout_seconds: int = 45) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(1.0)
            try:
                sock.connect((host, port))
            except OSError:
                time.sleep(1)
                continue
            return True
    return False


def detect_lan_ip() -> str:
    for command in (["ipconfig", "getifaddr", "en0"], ["ipconfig", "getifaddr", "en1"]):
        if shutil.which(command[0]) is None:
            continue
        result = run(command, check=False, capture_output=True)
        candidate = (result.stdout or "").strip()
        if candidate:
            return candidate

    if shutil.which("ifconfig") is None:
        return ""
    result = run(["ifconfig"], check=False, capture_output=True)
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("inet "):
            continue
        parts = line.split()
        if len(parts) >= 2 and not parts[1].startswith("127."):
            return parts[1]
    return ""


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
            "For non-Docker environments, run: uv run python scripts/dg.py test comprehensive --skip-smoke"
        )
        raise typer.Exit(1)


def infra_compose(args: list[str]) -> int:
    if compose_available():
        return run(["docker", "compose", "-f", str(COMPOSE_FILE), *args], check=False).returncode
    if docker_compose_available():
        return run(["docker-compose", "-f", str(COMPOSE_FILE), *args], check=False).returncode
    warning("Compose is unavailable; falling back to plain docker runtime.")
    return 125


def docker_runtime_up() -> None:
    run(["docker", "volume", "create", REDIS_VOLUME], check=True)

    existing = run(["docker", "ps", "-a", "--format", "{{.Names}}"], check=True, capture_output=True).stdout
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


def run_step(label: str, cmd: list[str]) -> None:
    info(f"=== {label} ===")
    code = run(cmd, check=False).returncode
    if code != 0:
        raise typer.Exit(code)


def assert_no_extra_args(extra_args: list[str], usage_hint: str) -> None:
    if not extra_args:
        return
    error(f"Unknown option(s): {' '.join(extra_args)}")
    typer.echo(usage_hint, err=True)
    raise typer.Exit(2)


def execute_infra_action(action: str) -> None:
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


def execute_test_backend() -> None:
    require_cmd("uv")
    run_step("ruff", ["uv", "run", "ruff", "check", "."])
    run_step(
        "ty",
        ["uv", "run", "ty", "check", ".", "--extra-search-path", "src", "--output-format", "concise"],
    )
    run_step("pytest", ["uv", "run", "pytest", "-q"])


@app.command("help")
def help_command() -> None:
    typer.echo(
        "\n".join(
            [
                "Usage:",
                "  uv run python scripts/dg.py dev [--no-api] [--no-web] [--no-scheduler]",
                "  uv run python scripts/dg.py infra [up|down|restart|status|logs]",
                "  uv run python scripts/dg.py readiness [base_url] [--strict-warnings]",
                "  uv run python scripts/dg.py test [backend|web|comprehensive] [--skip-e2e] [--skip-smoke] [--no-infra-bootstrap]",
                "  uv run python scripts/dg.py report nightly [date]",
                "  uv run python scripts/dg.py web env -- <command...>",
                "  uv run python scripts/dg.py help",
            ]
        )
    )


@app.command("dev")
def command_dev(
    no_api: Annotated[bool, typer.Option("--no-api", help="Do not start API service.")] = False,
    no_web: Annotated[bool, typer.Option("--no-web", help="Do not start web service.")] = False,
    no_scheduler: Annotated[
        bool, typer.Option("--no-scheduler", help="Do not start reminder scheduler.")
    ] = False,
) -> None:
    if no_api and no_web:
        error("Nothing to start: both --no-api and --no-web were set.")
        raise typer.Exit(2)

    load_root_env()
    require_cmd("uv")
    require_cmd("pnpm")

    start_scheduler = os.environ.get("START_REMINDER_SCHEDULER", "1")
    if no_scheduler:
        start_scheduler = "0"

    lan_ip = detect_lan_ip()
    lan_origin = f"http://{lan_ip}:3000" if lan_ip else ""
    default_api_cors = "http://localhost:3000,http://127.0.0.1:3000"
    default_next_allowed = "http://localhost:3000,http://127.0.0.1:3000"
    if lan_origin:
        default_api_cors = f"{default_api_cors},{lan_origin}"
        default_next_allowed = f"{default_next_allowed},{lan_origin}"

    os.environ.setdefault("API_CORS_ORIGINS", default_api_cors)
    os.environ.setdefault("NEXT_ALLOWED_DEV_ORIGINS", default_next_allowed)
    os.environ.setdefault("NEXT_PUBLIC_API_BASE_URL", "/backend")
    os.environ.setdefault("BACKEND_API_BASE_URL", "http://127.0.0.1:8001")
    os.environ.setdefault(
        "NEXT_PUBLIC_MEAL_ANALYZE_PROVIDER", os.environ.get("LLM_PROVIDER", "test")
    )
    os.environ.setdefault("API_DEV_LOG_VERBOSE", "1")
    os.environ.setdefault("API_DEV_LOG_HEADERS", "0")
    os.environ.setdefault("API_DEV_LOG_RESPONSE_HEADERS", "0")
    os.environ.setdefault("NEXT_PUBLIC_DEV_LOG_FRONTEND", "1")
    os.environ.setdefault("NEXT_PUBLIC_DEV_LOG_FRONTEND_VERBOSE", "0")
    os.environ["START_REMINDER_SCHEDULER"] = start_scheduler

    processes: list[subprocess.Popen[str]] = []

    def terminate_all() -> None:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        processes.clear()

    def _signal_handler(_signum: int, _frame: object) -> None:
        terminate_all()
        raise typer.Exit(130)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    if not no_api:
        info("starting API: uv run python -m apps.api.run")
        api_proc = subprocess.Popen(
            ["uv", "run", "python", "-m", "apps.api.run"],
            cwd=REPO_ROOT,
            text=True,
            env=os.environ.copy(),
        )
        processes.append(api_proc)

        if start_scheduler == "1":
            info("starting Reminder Scheduler: uv run python -m apps.api.run_reminder_scheduler")
            scheduler_proc = subprocess.Popen(
                ["uv", "run", "python", "-m", "apps.api.run_reminder_scheduler"],
                cwd=REPO_ROOT,
                text=True,
                env=os.environ.copy(),
            )
            processes.append(scheduler_proc)

    if not no_web:
        info("starting Web: pnpm web:dev")
        web_proc = subprocess.Popen(
            ["pnpm", "web:dev"],
            cwd=REPO_ROOT,
            text=True,
            env=os.environ.copy(),
        )
        processes.append(web_proc)

    for proc in processes:
        if proc.args:
            info(f"PID: {proc.pid} command={proc.args}")

    info(f"API_CORS_ORIGINS={os.environ['API_CORS_ORIGINS']}")
    info(f"NEXT_ALLOWED_DEV_ORIGINS={os.environ['NEXT_ALLOWED_DEV_ORIGINS']}")
    info(f"NEXT_PUBLIC_API_BASE_URL={os.environ['NEXT_PUBLIC_API_BASE_URL']}")
    info(f"BACKEND_API_BASE_URL={os.environ['BACKEND_API_BASE_URL']}")
    info(f"NEXT_PUBLIC_MEAL_ANALYZE_PROVIDER={os.environ['NEXT_PUBLIC_MEAL_ANALYZE_PROVIDER']}")
    info(
        "apps/web/.env override "
        + ("detected (applies to web:* scripts)" if (REPO_ROOT / "apps" / "web" / ".env").exists() else "not set")
    )
    info(
        "API_DEV_LOG_VERBOSE="
        f"{os.environ['API_DEV_LOG_VERBOSE']} API_DEV_LOG_HEADERS={os.environ['API_DEV_LOG_HEADERS']} "
        f"API_DEV_LOG_RESPONSE_HEADERS={os.environ['API_DEV_LOG_RESPONSE_HEADERS']}"
    )
    info(
        "NEXT_PUBLIC_DEV_LOG_FRONTEND="
        f"{os.environ['NEXT_PUBLIC_DEV_LOG_FRONTEND']} NEXT_PUBLIC_DEV_LOG_FRONTEND_VERBOSE="
        f"{os.environ['NEXT_PUBLIC_DEV_LOG_FRONTEND_VERBOSE']}"
    )
    info(f"START_REMINDER_SCHEDULER={os.environ['START_REMINDER_SCHEDULER']}")
    info("Press Ctrl+C to stop.")

    while processes:
        for proc in list(processes):
            code = proc.poll()
            if code is None:
                continue
            if code != 0:
                error("A dev process exited unexpectedly; stopping remaining services.")
                terminate_all()
                raise typer.Exit(1)
            processes.remove(proc)
        time.sleep(1)


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
    execute_infra_action(action)

@app.command("readiness")
def command_readiness(
    base_url: Annotated[str, typer.Argument(help="API base URL")] = "http://127.0.0.1:8001",
    strict_warnings: Annotated[
        bool, typer.Option("--strict-warnings/--no-strict-warnings", help="Fail on degraded status.")
    ] = False,
) -> None:
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


@test_app.command("backend", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def test_backend(ctx: typer.Context) -> None:
    assert_no_extra_args(ctx.args, "Usage: uv run python scripts/dg.py test backend")
    execute_test_backend()


@test_app.command("web")
def test_web(
    skip_e2e: Annotated[bool, typer.Option("--skip-e2e", help="Skip end-to-end tests.")] = False,
) -> None:
    require_cmd("pnpm")
    run_step("web:lint", ["pnpm", "web:lint"])
    run_step("web:typecheck", ["pnpm", "web:typecheck"])
    run_step("web:build", ["pnpm", "web:build"])
    if skip_e2e:
        info("Skipping web:e2e (--skip-e2e)")
    else:
        run_step("web:e2e", ["pnpm", "web:e2e"])


@test_app.command("comprehensive")
def test_comprehensive(
    skip_e2e: Annotated[bool, typer.Option("--skip-e2e", help="Skip web e2e tests.")] = False,
    skip_smoke: Annotated[bool, typer.Option("--skip-smoke", help="Skip legacy shared-topology smoke flow.")] = False,
    no_infra_bootstrap: Annotated[
        bool, typer.Option("--no-infra-bootstrap", help="Skip infra bootstrap in smoke flow.")
    ] = False,
) -> None:
    execute_test_backend()
    test_web(skip_e2e=skip_e2e)
    if skip_smoke:
        info("Skipping removed shared-topology smoke (--skip-smoke)")
        return

    if no_infra_bootstrap:
        info("Ignoring --no-infra-bootstrap in the SQLite-first runtime.")


@report_app.command("nightly")
def report_nightly(
    date_stamp: Annotated[str | None, typer.Argument(help="Date stamp YYYY-MM-DD.")] = None,
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


@web_app.command(
    "env",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
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


def main() -> None:
    if len(sys.argv) == 1:
        app(["help"], standalone_mode=False)
        return
    app()


if __name__ == "__main__":
    main()
