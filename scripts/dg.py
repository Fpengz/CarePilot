#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import json
from pathlib import Path
from typing import Annotated

import typer
from dotenv import dotenv_values

app = typer.Typer(help="Dietary Guardian unified developer CLI.")
infra_app = typer.Typer(help="Manage local infra (Postgres/Redis).")
migrate_app = typer.Typer(help="Run datastore migrations.")
smoke_app = typer.Typer(help="Run smoke checks.")
test_app = typer.Typer(help="Run validation suites.")
report_app = typer.Typer(help="Generate/locate reports.")
web_app = typer.Typer(help="Web helper commands.")

app.add_typer(infra_app, name="infra")
app.add_typer(migrate_app, name="migrate")
app.add_typer(smoke_app, name="smoke")
app.add_typer(test_app, name="test")
app.add_typer(report_app, name="report")
app.add_typer(web_app, name="web")

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPO_ROOT / "compose.dev.yml"
POSTGRES_CONTAINER = "dietary_guardian_dev_postgres"
REDIS_CONTAINER = "dietary_guardian_dev_redis"
POSTGRES_VOLUME = "dietary_guardian_dev_postgres_data"
REDIS_VOLUME = "dietary_guardian_dev_redis_data"
POSTGRES_IMAGE = "postgres:16-alpine"
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
    run(["docker", "volume", "create", POSTGRES_VOLUME], check=True)
    run(["docker", "volume", "create", REDIS_VOLUME], check=True)

    existing = run(["docker", "ps", "-a", "--format", "{{.Names}}"], check=True, capture_output=True).stdout
    names = set(existing.splitlines())

    if POSTGRES_CONTAINER not in names:
        run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                POSTGRES_CONTAINER,
                "--restart",
                "unless-stopped",
                "-e",
                "POSTGRES_DB=dietary_guardian",
                "-e",
                "POSTGRES_USER=dietary_guardian",
                "-e",
                "POSTGRES_PASSWORD=dietary_guardian",
                "-p",
                "5432:5432",
                "-v",
                f"{POSTGRES_VOLUME}:/var/lib/postgresql/data",
                POSTGRES_IMAGE,
            ],
            check=True,
        )
    else:
        run(["docker", "start", POSTGRES_CONTAINER], check=False)

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
    run(["docker", "rm", "-f", POSTGRES_CONTAINER, REDIS_CONTAINER], check=False)


def docker_runtime_status() -> None:
    run(
        [
            "docker",
            "ps",
            "--filter",
            f"name=^{POSTGRES_CONTAINER}$",
            "--filter",
            f"name=^{REDIS_CONTAINER}$",
            "--format",
            "table {{.Names}}\t{{.Status}}\t{{.Ports}}",
        ],
        check=True,
    )


def docker_runtime_logs() -> None:
    run(["docker", "logs", "--tail", "200", POSTGRES_CONTAINER], check=False)
    typer.echo("---")
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
        infra_run("up", ["-d", "postgres", "redis"])
        if not wait_for_tcp("127.0.0.1", 5432, timeout_seconds=60):
            error("Postgres did not become reachable on 127.0.0.1:5432 within timeout.")
            raise typer.Exit(1)
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
        infra_run("up", ["-d", "postgres", "redis"])
        info(f"Infra backend: {infra_backend_name()}")
        infra_run("ps")
        return
    if action == "status":
        info(f"Infra backend: {infra_backend_name()}")
        infra_run("ps")
        return
    info(f"Infra backend: {infra_backend_name()}")
    infra_run("logs", ["--tail=200", "postgres", "redis"])


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
                "  uv run python scripts/dg.py migrate postgres [--dsn <POSTGRES_DSN>]",
                "  uv run python scripts/dg.py migrate redis-keyspace [--redis-url <REDIS_URL>] [--namespace <REDIS_NAMESPACE>] [--apply]",
                "  uv run python scripts/dg.py smoke postgres-redis [--keep-running]",
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


@migrate_app.command("postgres")
def migrate_postgres(
    dsn: Annotated[
        str | None,
        typer.Option("--dsn", help="Postgres DSN. Defaults to POSTGRES_DSN env var or local dev DSN."),
    ] = None,
) -> None:
    load_root_env()
    postgres_dsn = dsn or os.environ.get(
        "POSTGRES_DSN",
        "postgresql://dietary_guardian:dietary_guardian@127.0.0.1:5432/dietary_guardian",
    )
    require_cmd("uv")
    env = os.environ.copy()
    env["POSTGRES_DSN"] = postgres_dsn
    code = run(
        ["uv", "run", "python", "-m", "dietary_guardian.infrastructure.persistence.postgres_schema", postgres_dsn],
        check=False,
        env=env,
    ).returncode
    if code != 0:
        raise typer.Exit(code)


@migrate_app.command("redis-keyspace")
def migrate_redis_keyspace(
    redis_url: Annotated[str | None, typer.Option("--redis-url", help="Redis URL to migrate.")] = None,
    namespace: Annotated[
        str, typer.Option("--namespace", help="Redis namespace to migrate.")
    ] = "dietary_guardian",
    apply: Annotated[bool, typer.Option("--apply", help="Apply migration changes.")] = False,
) -> None:
    load_root_env()
    effective_redis_url = redis_url or os.environ.get("REDIS_URL", "")
    if not effective_redis_url:
        error("REDIS_URL is required. Pass --redis-url or set REDIS_URL in environment.")
        raise typer.Exit(2)

    require_cmd("uv")
    command = [
        "uv",
        "run",
        "python",
        "scripts/migrate-redis-keyspace.py",
        "--redis-url",
        effective_redis_url,
        "--namespace",
        namespace,
    ]
    if apply:
        command.append("--apply")
    code = run(command, check=False).returncode
    if code != 0:
        raise typer.Exit(code)


@smoke_app.command("postgres-redis")
def smoke_postgres_redis(
    keep_running: Annotated[bool, typer.Option("--keep-running", help="Leave API+worker running.")] = False,
) -> None:
    load_root_env()
    require_cmd("curl")
    require_cmd("uv")

    os.environ.setdefault("LLM_PROVIDER", "test")
    os.environ.setdefault("APP_DATA_BACKEND", "postgres")
    os.environ.setdefault("AUTH_STORE_BACKEND", "postgres")
    os.environ.setdefault("HOUSEHOLD_STORE_BACKEND", "postgres")
    os.environ.setdefault("EPHEMERAL_STATE_BACKEND", "redis")
    os.environ.setdefault(
        "POSTGRES_DSN", "postgresql://dietary_guardian:dietary_guardian@127.0.0.1:5432/dietary_guardian"
    )
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
    os.environ.setdefault("REDIS_WORKER_SIGNAL_CHANNEL", "workers.ready")
    os.environ.setdefault("API_HOST", "127.0.0.1")
    os.environ.setdefault("API_PORT", "8001")
    os.environ.setdefault("WORKER_MODE", "external")

    api_host = os.environ["API_HOST"]
    api_port = os.environ["API_PORT"]
    api_log = Path(os.environ.get("TMPDIR", "/tmp")) / "dg_api_postgres_redis.log"
    worker_log = Path(os.environ.get("TMPDIR", "/tmp")) / "dg_worker_postgres_redis.log"
    cookie_jar = Path(os.environ.get("TMPDIR", "/tmp")) / "dg_smoke_cookies.txt"

    if os.environ.get("DG_SMOKE_SKIP_INFRA_BOOTSTRAP", "0") != "1":
        execute_infra_action("up")
        migrate_postgres(dsn=None)
    else:
        info("DG_SMOKE_SKIP_INFRA_BOOTSTRAP=1; skipping infra up and postgres migration bootstrap.")

    if cookie_jar.exists():
        cookie_jar.unlink()

    api_proc = subprocess.Popen(
        ["uv", "run", "python", "-m", "apps.api.run"],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        stdout=api_log.open("w"),
        stderr=subprocess.STDOUT,
        text=True,
    )
    worker_proc = subprocess.Popen(
        ["uv", "run", "python", "-m", "apps.workers.run"],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        stdout=worker_log.open("w"),
        stderr=subprocess.STDOUT,
        text=True,
    )

    def cleanup() -> None:
        for proc in (api_proc, worker_proc):
            if proc.poll() is None:
                proc.terminate()
        for proc in (api_proc, worker_proc):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    try:
        live_ok = False
        for _ in range(40):
            if (
                run(
                    ["curl", "-sf", f"http://{api_host}:{api_port}/api/v1/health/live"],
                    check=False,
                ).returncode
                == 0
            ):
                live_ok = True
                break
            time.sleep(1)
        if not live_ok:
            error("API health/live did not become ready in time.")
            if api_log.exists():
                typer.echo(api_log.read_text()[-8000:], err=True)
            raise typer.Exit(1)

        run(["curl", "-sf", f"http://{api_host}:{api_port}/api/v1/health/ready"], check=True)

        login_response = run(
            [
                "curl",
                "-sf",
                "-c",
                str(cookie_jar),
                "-b",
                str(cookie_jar),
                "-H",
                "Content-Type: application/json",
                "-d",
                '{"email":"member@example.com","password":"member-pass"}',
                f"http://{api_host}:{api_port}/api/v1/auth/login",
            ],
            check=True,
            capture_output=True,
        ).stdout
        login_payload = json.loads(login_response)
        if login_payload.get("user", {}).get("email") != "member@example.com":
            error("unexpected login response payload")
            raise typer.Exit(1)

        generate_response = run(
            [
                "curl",
                "-sf",
                "-c",
                str(cookie_jar),
                "-b",
                str(cookie_jar),
                "-X",
                "POST",
                f"http://{api_host}:{api_port}/api/v1/reminders/generate",
            ],
            check=True,
            capture_output=True,
        ).stdout

        generate_payload = json.loads(generate_response)
        reminders = generate_payload.get("reminders") or []
        if not reminders:
            error("no reminders generated")
            raise typer.Exit(1)
        reminder_id_str = str(reminders[0]["id"])

        # Smoke flow must be deterministic regardless of current wall-clock timezone.
        # Shift generated schedules for the probed reminder to "now" so worker delivery can be observed.
        shift_code = (
            "from datetime import datetime, timezone\n"
            "from apps.api.dietary_api.deps import build_app_context, close_app_context\n"
            "import os\n"
            "rid = os.environ['DG_SMOKE_REMINDER_ID']\n"
            "ctx = build_app_context()\n"
            "try:\n"
            "    now = datetime.now(timezone.utc)\n"
            "    for item in ctx.app_store.list_scheduled_notifications(reminder_id=rid):\n"
            "        ctx.app_store.set_scheduled_notification_trigger_at(item.id, now)\n"
            "    ctx.coordination_store.publish_signal('workers.ready', {'reminder_id': rid, 'reason': 'smoke-trigger-now'})\n"
            "    ctx.coordination_store.publish_signal('reminders.ready', {'reminder_id': rid, 'reason': 'smoke-trigger-now'})\n"
            "finally:\n"
            "    close_app_context(ctx)\n"
        )
        shift_env = os.environ.copy()
        shift_env["DG_SMOKE_REMINDER_ID"] = reminder_id_str
        run(
            ["uv", "run", "python", "-c", shift_code],
            check=True,
            env=shift_env,
        )

        delivered = False
        for _ in range(25):
            schedules = run(
                [
                    "curl",
                    "-sf",
                    "-c",
                    str(cookie_jar),
                    "-b",
                    str(cookie_jar),
                    f"http://{api_host}:{api_port}/api/v1/reminders/{reminder_id_str}/notification-schedules",
                ],
                check=True,
                capture_output=True,
            ).stdout
            schedules_payload = json.loads(schedules)
            items = schedules_payload.get("items") or []
            statuses = {item.get("status") for item in items}
            if items and "delivered" in statuses:
                delivered = True
                break
            time.sleep(1)

        if not delivered:
            error("notification schedules did not reach delivered state in time.")
            error("API log tail:")
            if api_log.exists():
                typer.echo(api_log.read_text()[-8000:], err=True)
            error("Worker log tail:")
            if worker_log.exists():
                typer.echo(worker_log.read_text()[-8000:], err=True)
            raise typer.Exit(1)

        info("success: postgres+redis API and worker flow is healthy.")
        info(f"API log: {api_log}")
        info(f"Worker log: {worker_log}")
        if keep_running:
            info("--keep-running requested; API and worker remain active.")
            info(f"API PID={api_proc.pid} Worker PID={worker_proc.pid}")
            raise typer.Exit(0)
    finally:
        if not keep_running:
            cleanup()


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
    skip_smoke: Annotated[bool, typer.Option("--skip-smoke", help="Skip postgres-redis smoke flow.")] = False,
    no_infra_bootstrap: Annotated[
        bool, typer.Option("--no-infra-bootstrap", help="Skip infra bootstrap in smoke flow.")
    ] = False,
) -> None:
    execute_test_backend()
    test_web(skip_e2e=skip_e2e)
    if skip_smoke:
        info("Skipping postgres-redis smoke (--skip-smoke)")
        return

    if no_infra_bootstrap:
        os.environ["DG_SMOKE_SKIP_INFRA_BOOTSTRAP"] = "1"
    smoke_postgres_redis(keep_running=False)


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
