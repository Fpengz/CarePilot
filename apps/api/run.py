"""Module for run."""

import uvicorn

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.app import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        create_app(),
        host=settings.api.host,
        port=settings.api.port,
        reload=False,
        log_level=settings.observability.log_level.lower(),
    )


if __name__ == "__main__":
    main()

