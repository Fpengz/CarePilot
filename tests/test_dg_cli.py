import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DG = ROOT / "scripts" / "dg.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(DG), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def test_help_lists_new_migrate_and_test_commands() -> None:
    result = _run("help")
    assert result.returncode == 0
    output = result.stdout
    assert "migrate redis-keyspace" not in output
    assert "test [backend|web|comprehensive]" in output
    assert "web env -- <command...>" in output


def test_test_command_help_is_available() -> None:
    result = _run("test", "--help")
    assert result.returncode == 0
    assert "comprehensive" in result.stdout


def test_redis_keyspace_migration_command_is_removed() -> None:
    result = _run("migrate", "redis-keyspace")
    assert result.returncode != 0
    assert "No such command 'redis-keyspace'" in (result.stderr or result.stdout)
