"""Backward-compatibility shim — import from dietary_guardian.observability instead."""
# ruff: noqa: F401
import sys
import types

import dietary_guardian.observability.setup as _setup_module
from dietary_guardian.observability.setup import (
    _CONFIGURED,
    _HANDLER_MARKER,
    _ROOT_MARKER,
    _dedupe_logfire_handlers,
    _has_logfire_handler,
    _resolve_log_level_name,
    get_logger,
    logger,
    logfire_api,
    setup_logging,
)

logfire = _setup_module.logfire


class _ShimModule(types.ModuleType):
    """Module subclass that forwards attribute writes to the canonical setup module.

    This ensures that test code which resets `_CONFIGURED` via
    ``logging_config._CONFIGURED = False`` properly affects the live state in
    ``observability.setup``.
    """

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        if hasattr(_setup_module, name):
            setattr(_setup_module, name, value)


sys.modules[__name__].__class__ = _ShimModule
