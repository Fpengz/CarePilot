"""Meta-architecture checks for workflow refactor boundaries."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _all_python_files() -> list[Path]:
    return (
        sorted((ROOT / "src").rglob("*.py"))
        + sorted((ROOT / "apps").rglob("*.py"))
        + [p for p in sorted((ROOT / "tests").rglob("*.py")) if p.name != Path(__file__).name]
    )


def test_workflow_coordinator_is_removed() -> None:
    offenders: list[str] = []
    for path in _all_python_files():
        text = path.read_text(encoding="utf-8")
        if "WorkflowCoordinator" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_workflow_contract_snapshots_are_removed() -> None:
    offenders: list[str] = []
    needles = ("workflow_contract_snapshots", "WorkflowContractSnapshot")
    for path in _all_python_files():
        text = path.read_text(encoding="utf-8")
        if any(needle in text for needle in needles):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
