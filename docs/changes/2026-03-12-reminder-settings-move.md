Reminder delivery settings relocation.

Summary:
- Moved reminder delivery preferences from the Reminders page to Settings.
- Kept mobility reminder configuration under Settings alongside delivery channels.
- Updated reminders page copy to point users to Settings for delivery preferences.

Tests:
- `uv run python scripts/cli.py web env -- pnpm --dir apps/web build`
- `uv run python scripts/cli.py web env -- pnpm --dir apps/web exec playwright test --grep "reminder delivery settings live in settings"`
