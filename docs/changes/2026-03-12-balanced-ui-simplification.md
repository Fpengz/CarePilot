# Balanced UI Simplification (2026-03-12)

## Summary
Applied a balanced simplification pass across all web pages: one primary panel per page, one supporting rail, and reduced nested borders to create a calmer, more premium interface.

## Highlights
- Introduced `section-stack` for calmer vertical rhythm across secondary rails.
- Softened navigation and list borders via `--border-soft`.
- Chat redesigned into a two-column workspace with a clinical panel and a context rail.
- Dashboard, reports, symptoms, reminders, and workflow pages adopt the new spacing rhythm.

## Validation
- `pnpm web:lint`
- `pnpm web:typecheck`
