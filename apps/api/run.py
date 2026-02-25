import uvicorn

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        create_app(),
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.dietary_guardian_log_level.lower(),
    )


if __name__ == "__main__":
    main()

