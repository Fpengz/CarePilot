"""Knowledge base structure validation."""

from __future__ import annotations

import sys
from subprocess import run


def test_knowledge_base_validation() -> None:
    result = run(
        [sys.executable, "scripts/docs/validate_knowledge_base.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
