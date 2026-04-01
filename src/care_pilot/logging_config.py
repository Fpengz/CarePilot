"""
Provide a backward-compatibility logging shim.

This module preserves legacy imports and forwards to the observability setup.
"""

# ruff: noqa: F401
import sys
import types

import care_pilot.platform.observability.logging as _logging_module
import logfire
from care_pilot.platform.observability.logging import (
    _CONFIGURED,
    _HANDLER_MARKER,
    _ROOT_MARKER,
    _dedupe_logfire_handlers,
    _has_logfire_handler,
    _resolve_log_level_name,
    get_logger,
    logfire_api,
    logger,
    setup_logging,
)


class _ShimModule(types.ModuleType):
    """Module subclass that forwards attribute writes to the canonical logging module.

    This ensures that test code which resets `_CONFIGURED` via
    ``logging_config._CONFIGURED = False`` properly affects the live state in
    ``observability.logging``.
    """

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        if hasattr(_logging_module, name):
            setattr(_logging_module, name, value)


sys.modules[__name__].__class__ = _ShimModule
