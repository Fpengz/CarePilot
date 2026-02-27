from dietary_guardian.config.settings import get_settings


def validate_runtime_config() -> None:
    settings = get_settings()
    if settings.session_secret == "dev-insecure-session-secret-change-me":
        raise RuntimeError("SESSION_SECRET must be overridden for deployment")


def main() -> None:
    validate_runtime_config()


if __name__ == "__main__":
    main()
