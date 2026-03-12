# Mem0 Chat Memory (2026-03-13)

## Summary
- Added a Mem0-backed memory store for chat personalization.
- Chat now retrieves top-k memories per user and injects them into the chat context.
- Chat turns are recorded back into Mem0 after responses complete.

## Configuration
Environment variables:
- `MEM0_API_KEY`
- `MEM0_BASE_URL` (optional)
- `MEM0_ENABLED` (default false)
- `MEM0_TOP_K` (default 5)

## Notes
- Memory calls are best-effort and do not block chat if Mem0 is unavailable.
- Scope is chat-only for now.
