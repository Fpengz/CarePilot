"""Module for runtime validate."""

from dietary_guardian.config.settings import get_settings


def validate_runtime_config() -> None:
    # get_settings() triggers model validation and raises on invalid deployment config.
    get_settings()


def main() -> None:
    validate_runtime_config()


if __name__ == "__main__":
    main()
