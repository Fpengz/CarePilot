"""Architecture tests that keep model plumbing inside the agent layer.

These checks are intentionally simple string scans. They are not meant to be a
perfect linter; they are a guardrail to prevent the most expensive and
hard-to-debug regressions:
- importing `pydantic_ai.Agent` outside `care_pilot.agent`
- calling `LLMFactory.get_model()` outside `care_pilot.agent`

Rationale: LLM calls are expensive and should be centralized behind the agent
runtime so contracts, retries, and tracing stay consistent.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _iter_python_files(relative_root: str) -> list[Path]:
    base = ROOT / relative_root
    if not base.exists():
        return []
    return [path for path in base.rglob("*.py") if path.is_file()]


def test_no_pydantic_ai_agent_import_outside_agent_layer() -> None:
    offenders: list[str] = []
    for path in _iter_python_files("src/care_pilot"):
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith("src/care_pilot/agent/"):
            continue
        contents = path.read_text(encoding="utf-8")
        if "from pydantic_ai import Agent" in contents:
            offenders.append(relative)
    assert (
        offenders == []
    ), f"Move `pydantic_ai.Agent` usage into `care_pilot.agent`: {offenders}"


def test_no_llm_factory_get_model_outside_agent_layer() -> None:
    offenders: list[str] = []
    for path in _iter_python_files("src/care_pilot"):
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith("src/care_pilot/agent/"):
            continue
        contents = path.read_text(encoding="utf-8")
        if "LLMFactory.get_model(" in contents:
            offenders.append(relative)
    assert (
        offenders == []
    ), f"Move `LLMFactory.get_model()` usage into `care_pilot.agent`: {offenders}"
