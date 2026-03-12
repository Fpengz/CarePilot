Chat streaming stability tweaks.

Summary:
- Reduced scroll jitter by using auto-scroll during live streaming.
- Reserved minimal height for the streaming assistant bubble to limit layout shift.

Tests:
- `pnpm web:lint`
