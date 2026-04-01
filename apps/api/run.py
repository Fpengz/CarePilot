"""
Launch the dietary API via Uvicorn.

This entrypoint loads configuration and starts the FastAPI application
using the runtime settings.
"""

import uvicorn

from apps.api.carepilot_api.main import create_app
from care_pilot.config.app import get_settings
from care_pilot.platform.observability import setup_observability


def main() -> None:
    settings = get_settings()
    setup_observability()
    uvicorn.run(
        create_app(),
        host=settings.api.host,
        port=settings.api.port,
        reload=False,
        log_level=settings.observability.log_level.lower(),
        log_config=None,
    )


if __name__ == "__main__":
    main()
