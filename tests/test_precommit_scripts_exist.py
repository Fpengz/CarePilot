from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_precommit_scripts_are_present_and_executable() -> None:
    ruff_script = ROOT / "tools" / "precommit_ruff.sh"
    ty_script = ROOT / "tools" / "precommit_ty.sh"
    readiness_script = ROOT / "scripts" / "check-readiness.sh"

    assert ruff_script.exists()
    assert ty_script.exists()
    assert readiness_script.exists()
    assert ruff_script.stat().st_mode & 0o111
    assert ty_script.stat().st_mode & 0o111
    assert readiness_script.stat().st_mode & 0o111
