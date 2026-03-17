"""Pytest fixtures and shared test configuration."""

import logging
import sys
from pathlib import Path

# Ensure src-layout package imports (care_pilot.*) work under plain `uv run pytest`.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
src_str = str(SRC)
if src_str not in sys.path:
    sys.path.insert(0, src_str)


def pytest_sessionfinish(session, exitstatus):
    """Shut down logging to avoid I/O errors when streams are closed by pytest."""
    logging.shutdown()
    # Remove all handlers from all loggers to prevent any late-arriving log
    # messages from trying to use closed streams.
    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.handlers = []
    logging.getLogger().handlers = []
