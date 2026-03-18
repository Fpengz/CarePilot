from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from collections.abc import Mapping, MutableMapping
from pathlib import Path

import typer
from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "compose.dev.yml"
REDIS_CONTAINER = "care_pilot_dev_redis"
REDIS_VOLUME = "care_pilot_dev_redis_data"
REDIS_IMAGE = "redis:7-alpine"


def info(message: str) -> None:
    typer.echo(f"[CarePilot] {message}")


def warning(message: str) -> None:
    typer.echo(f"[CarePilot] warning: {message}", err=True)


def error(message: str) -> None:
    typer.echo(f"[CarePilot] error: {message}", err=True)


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


def apply_dev_env_defaults(env: MutableMapping[str, str]) -> None:
    env.setdefault("CARE_PILOT_LOG_LEVEL", "DEBUG")


def emit_env_snapshot(env: Mapping[str, str]) -> None:
    redacted_markers = ("KEY", "TOKEN", "SECRET", "PASSWORD")
    lines = ["Runtime environment:"]
    for key in sorted(env):
        value = env[key]
        if any(marker in key.upper() for marker in redacted_markers):
            value = "<redacted>"
        lines.append(f"{key}={value}")
    typer.echo("\n".join(lines))


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
    for command in (
        ["ipconfig", "getifaddr", "en0"],
        ["ipconfig", "getifaddr", "en1"],
    ):
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
