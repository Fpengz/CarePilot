"""Tests for dev CLI environment defaults."""

from scripts import cli


def test_dev_env_defaults_sets_log_level_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("CARE_PILOT_LOG_LEVEL", raising=False)
    env = {}

    cli.apply_dev_env_defaults(env)

    assert env["CARE_PILOT_LOG_LEVEL"] == "DEBUG"


def test_dev_env_defaults_preserves_existing_log_level(monkeypatch) -> None:
    monkeypatch.setenv("CARE_PILOT_LOG_LEVEL", "INFO")
    env = {"CARE_PILOT_LOG_LEVEL": "INFO"}

    cli.apply_dev_env_defaults(env)

    assert env["CARE_PILOT_LOG_LEVEL"] == "INFO"
