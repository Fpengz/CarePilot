import logging
import os
from typing import Any, cast

import logfire

logfire_api = cast(Any, logfire)
_CONFIGURED = False

def setup_logging(project_name: str = "dietary-guardian"):
    """
    Configures logfire and standard logging for clinical-grade observability.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return logging.getLogger(project_name)

    # 1. Initialize Logfire (2026 standard for Pydantic-AI)
    logfire_api.configure(send_to_logfire=False)

    # 2. Configure standard logging to work with logfire
    level_name = os.getenv("DIETARY_GUARDIAN_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[cast(logging.Handler, logfire.LogfireLoggingHandler())],
    )
    logger = logging.getLogger(project_name)
    logger.setLevel(level)
    _CONFIGURED = True
    return logger


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)

# Global logger instance
logger = get_logger("dietary-guardian")
