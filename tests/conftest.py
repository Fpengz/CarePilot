"""Pytest fixtures and shared test configuration."""

import logging
import sys
from pathlib import Path

import pytest

from care_pilot.config.app import get_settings

# Ensure src-layout package imports (care_pilot.*) work under plain `uv run pytest`.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
src_str = str(SRC)
if src_str not in sys.path:
    sys.path.insert(0, src_str)


@pytest.fixture(autouse=True)
def _test_llm_defaults(monkeypatch: pytest.MonkeyPatch):
    """Force test-safe LLM defaults to prevent external network calls."""
    monkeypatch.setenv("LLM_PROVIDER", "test")
    monkeypatch.setenv("EMOTION_INFERENCE_ENABLED", "false")
    monkeypatch.setenv("EMOTION_SPEECH_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def pytest_sessionfinish(session, exitstatus):
    """Shut down logging to avoid I/O errors when streams are closed by pytest."""
    logging.shutdown()
    # Remove all handlers from all loggers to prevent any late-arriving log
    # messages from trying to use closed streams.
    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.handlers = []
    logging.getLogger().handlers = []


@pytest.fixture
def sqlite_meal_env(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Provide a sqlite-backed auth + API store for meal tests."""
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
