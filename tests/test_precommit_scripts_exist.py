from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_precommit_scripts_are_present_and_executable() -> None:
    dg_cli_script = ROOT / "scripts" / "dg.py"
    redis_migrate_script = ROOT / "scripts" / "migrate-redis-keyspace.py"

    assert dg_cli_script.exists()
    assert redis_migrate_script.exists()
    assert dg_cli_script.stat().st_mode & 0o111
    assert redis_migrate_script.stat().st_mode & 0o111
