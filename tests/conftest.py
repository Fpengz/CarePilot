"""Pytest fixtures and shared test configuration."""

import sys
from pathlib import Path

# Ensure src-layout package imports (dietary_guardian.*) work under plain `uv run pytest`.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
src_str = str(SRC)
if src_str not in sys.path:
    sys.path.insert(0, src_str)
