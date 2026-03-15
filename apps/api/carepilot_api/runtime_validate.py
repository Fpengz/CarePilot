"""
Validate API runtime configuration at startup.

This module triggers settings validation to catch misconfigured deployments
early in startup or health checks.
"""

from care_pilot.config.app import get_settings


def validate_runtime_config() -> None:
    # get_settings() triggers model validation and raises on invalid deployment config.
    get_settings()


def main() -> None:
    validate_runtime_config()


if __name__ == "__main__":
    main()
