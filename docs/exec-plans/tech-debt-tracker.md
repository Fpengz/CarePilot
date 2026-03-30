# Tech Debt Tracker

This tracker captures known debt that affects correctness, operability, or maintainability. Keep it short and prioritized.

| Item | Status | Owner | Last Verified | Notes |
| --- | --- | --- | --- | --- |
| Clarify production infra assumptions (Redis, vector memory, worker queues) | active | platform | 2026-03-30 | Document required vs optional services and default behaviors. |
| Align runtime configuration defaults with docs | active | platform | 2026-03-30 | Ensure config reference and actual defaults match. |
| Inference/runtime deployment guidance | active | agent | 2026-03-30 | Spell out API vs workers vs inference runtime boundaries. |
