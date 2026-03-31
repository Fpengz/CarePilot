"""CLI commands for project versioning."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console

version_app = typer.Typer(help="Manage project version.")
console = Console()

REPO_ROOT = Path(__file__).resolve().parents[3]
PYPROJECT_TOML = REPO_ROOT / "pyproject.toml"
PACKAGE_JSON = REPO_ROOT / "apps/web/package.json"


def get_current_version() -> str:
    """Read version from pyproject.toml."""
    content = PYPROJECT_TOML.read_text()
    match = re.search(r'^version = "([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def update_version(new_version: str) -> None:
    """Update version in all tracked files."""
    # Update pyproject.toml
    content = PYPROJECT_TOML.read_text()
    new_content = re.sub(
        r'^version = "[^"]+"', f'version = "{new_version}"', content, flags=re.MULTILINE
    )
    PYPROJECT_TOML.write_text(new_content)

    # Update package.json
    if PACKAGE_JSON.exists():
        data = json.loads(PACKAGE_JSON.read_text())
        data["version"] = new_version
        PACKAGE_JSON.write_text(json.dumps(data, indent=2) + "\n")


def bump_semver(version: str, part: Literal["patch", "minor", "major"]) -> str:
    """Increment semver string."""
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid semver: {version}")

    major, minor, patch = map(int, parts)
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1

    return f"{major}.{minor}.{patch}"


@version_app.command("status")
def status() -> None:
    """Show current version."""
    try:
        v = get_current_version()
        console.print(f"Current version: [bold green]{v}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1) from e


@version_app.command("patch")
def bump_patch() -> None:
    """Increment patch version (0.0.x)."""
    _bump("patch")


@version_app.command("minor")
def bump_minor() -> None:
    """Increment minor version (0.x.0)."""
    _bump("minor")


@version_app.command("major")
def bump_major() -> None:
    """Increment major version (x.0.0)."""
    _bump("major")


@version_app.command("set")
def set_version(version: str) -> None:
    """Set version to a specific value."""
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        console.print(f"[bold red]Error:[/bold red] {version} is not a valid semver (x.y.z)")
        raise typer.Exit(1)

    old = get_current_version()
    update_version(version)
    console.print(f"Version updated: [yellow]{old}[/yellow] -> [bold green]{version}[/bold green]")


def _bump(part: Literal["patch", "minor", "major"]) -> None:
    old = get_current_version()
    new = bump_semver(old, part)
    update_version(new)
    console.print(f"Version bumped ({part}): [yellow]{old}[/yellow] -> [bold green]{new}[/bold green]")
