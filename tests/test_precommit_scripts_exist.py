from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_precommit_scripts_are_present_and_executable() -> None:
    dg_cli_script = ROOT / "scripts" / "dg.py"

    assert dg_cli_script.exists()
    assert dg_cli_script.stat().st_mode & 0o111
