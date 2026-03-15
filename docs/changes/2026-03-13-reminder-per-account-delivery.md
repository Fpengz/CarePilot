# Reminder delivery now respects per-account destinations.

Summary:
- Telegram reminder delivery in the outbox path now uses the per-user destination payload when provided.
- The Telegram channel accepts destination overrides while preserving the default environment fallback.
- Tests cover destination override behavior and updated Telegram helpers.

## Files touched
- `src/care_pilot/platform/messaging/channels/telegram.py`
- `src/care_pilot/platform/messaging/channels/sinks.py`
- `tests/infrastructure/test_channel_destination_overrides.py`
- `tests/infrastructure/test_telegram_channel_dev.py`
- `tests/application/test_notification_service.py`
- `TODO.md`

## Validation
```
uv run pytest -q tests/infrastructure/test_channel_destination_overrides.py
uv run pytest -q tests/infrastructure/test_telegram_channel_dev.py tests/application/test_notification_service.py
```
