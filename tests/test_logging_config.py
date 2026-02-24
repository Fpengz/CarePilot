import logging

import dietary_guardian.logging_config as logging_config


class _DummyLogfireHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - no-op test handler
        del record


def test_setup_logging_is_idempotent(monkeypatch) -> None:
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_configured = logging_config._CONFIGURED
    root_marker_exists = hasattr(root, logging_config._ROOT_MARKER)
    original_root_marker = getattr(root, logging_config._ROOT_MARKER, False)
    original_logfire_handler = logging_config.logfire.LogfireLoggingHandler
    original_logfire_configure = logging_config.logfire_api.configure

    try:
        root.handlers = []
        if hasattr(root, logging_config._ROOT_MARKER):
            delattr(root, logging_config._ROOT_MARKER)
        logging_config._CONFIGURED = False
        monkeypatch.setattr(logging_config.logfire, "LogfireLoggingHandler", _DummyLogfireHandler)
        monkeypatch.setattr(logging_config.logfire_api, "configure", lambda **_: None)

        logging_config.setup_logging("dietary-guardian-test")
        logging_config._CONFIGURED = False
        logging_config.setup_logging("dietary-guardian-test")

        tagged_handlers = [h for h in root.handlers if getattr(h, logging_config._HANDLER_MARKER, False)]
        assert len(tagged_handlers) == 1
    finally:
        root.handlers = original_handlers
        logging_config._CONFIGURED = original_configured
        monkeypatch.setattr(logging_config.logfire, "LogfireLoggingHandler", original_logfire_handler)
        monkeypatch.setattr(logging_config.logfire_api, "configure", original_logfire_configure)
        if root_marker_exists:
            setattr(root, logging_config._ROOT_MARKER, original_root_marker)
        elif hasattr(root, logging_config._ROOT_MARKER):
            delattr(root, logging_config._ROOT_MARKER)
