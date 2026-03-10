"""Tests for dietary agent import."""

import os
import subprocess
import sys
from pathlib import Path


def test_import_dietary_agent_without_gemini_keys_does_not_fail() -> None:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["LLM_PROVIDER"] = "gemini"
    env.pop("GEMINI_API_KEY", None)
    env.pop("GOOGLE_API_KEY", None)
    env["PYTHONPATH"] = str(root / "src")

    result = subprocess.run(
        [sys.executable, "-c", "import dietary_guardian.agents.dietary"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
