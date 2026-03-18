from __future__ import annotations

import os
import signal
import subprocess
import time
from typing import Annotated

import typer
from scripts.cli.utils import (
    REPO_ROOT,
    apply_dev_env_defaults,
    detect_lan_ip,
    emit_env_snapshot,
    error,
    info,
    load_root_env,
    require_cmd,
)

dev_app = typer.Typer(help="Start development services.")


@dev_app.callback(invoke_without_command=True)
def dev_default(
    ctx: typer.Context,
    no_api: Annotated[bool, typer.Option("--no-api", help="Do not start API service.")] = False,
    no_web: Annotated[bool, typer.Option("--no-web", help="Do not start web service.")] = False,
    no_scheduler: Annotated[
        bool,
        typer.Option("--no-scheduler", help="Do not start reminder scheduler."),
    ] = False,
    no_sqlite_reminder_worker: Annotated[
        bool,
        typer.Option(
            "--no-sqlite-reminder-worker",
            help="Do not start SQLite reminder worker.",
        ),
    ] = False,
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    if no_api and no_web:
        error("Nothing to start: both --no-api and --no-web were set.")
        raise typer.Exit(2)

    load_root_env()
    require_cmd("uv")
    require_cmd("pnpm")
    apply_dev_env_defaults(os.environ)

    start_scheduler = os.environ.get("START_REMINDER_SCHEDULER", "1")
    if no_scheduler:
        start_scheduler = "0"

    start_sqlite_reminder_worker = os.environ.get("START_SQLITE_REMINDER_WORKER", "1")
    if no_sqlite_reminder_worker:
        start_sqlite_reminder_worker = "0"

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
        "NEXT_PUBLIC_MEAL_ANALYZE_PROVIDER",
        os.environ.get("LLM_PROVIDER", "test"),
    )
    os.environ.setdefault("API_DEV_LOG_VERBOSE", "1")
    os.environ.setdefault("API_DEV_LOG_HEADERS", "0")
    os.environ.setdefault("API_DEV_LOG_RESPONSE_HEADERS", "0")
    os.environ.setdefault("NEXT_PUBLIC_DEV_LOG_FRONTEND", "1")
    os.environ.setdefault("NEXT_PUBLIC_DEV_LOG_FRONTEND_VERBOSE", "0")
    os.environ["START_REMINDER_SCHEDULER"] = start_scheduler
    os.environ["START_SQLITE_REMINDER_WORKER"] = start_sqlite_reminder_worker
    emit_env_snapshot(os.environ)

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
                [
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "apps.api.run_reminder_scheduler",
                ],
                cwd=REPO_ROOT,
                text=True,
                env=os.environ.copy(),
            )
            processes.append(scheduler_proc)

        if start_sqlite_reminder_worker == "1":
            info("starting SQLite Reminder Worker: uv run python -m apps.workers.reminder_worker")
            sqlite_worker_proc = subprocess.Popen(
                ["uv", "run", "python", "-m", "apps.workers.reminder_worker"],
                cwd=REPO_ROOT,
                text=True,
                env=os.environ.copy(),
            )
            processes.append(sqlite_worker_proc)

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

    exit_code = 0
    try:
        while processes:
            for proc in list(processes):
                status = proc.poll()
                if status is not None:
                    if status != 0 and exit_code == 0:
                        exit_code = status
                    processes.remove(proc)
            time.sleep(1)
    finally:
        terminate_all()

    if exit_code:
        raise typer.Exit(exit_code)
