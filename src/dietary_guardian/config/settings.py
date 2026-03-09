"""Stable settings import surface used across the codebase."""

from dietary_guardian.config.app import AppSettings, get_settings

Settings = AppSettings

__all__ = ["AppSettings", "Settings", "get_settings"]
