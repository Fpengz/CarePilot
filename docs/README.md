# Documentation Index

This directory is the system of record for CarePilot repository knowledge. Start here, then drill into the relevant index. Keep docs concise, current, and cross-linked.

## Primary Maps
- `docs/design-docs/index.md` — architecture and design beliefs (including core beliefs)
- `docs/exec-plans/index.md` — active/in-progress/completed execution plans + templates
- `docs/product-specs/index.md` — product specs and user-facing behavior
- `docs/references/index.md` — API, ops, config, and engineering references
- `docs/design-docs/architecture/event-driven/ARCHITECTURE.md` — primary event-driven architecture (orchestration-first is legacy)

## Canonical Root Docs
- `README.md` — product overview and setup
- `ARCHITECTURE.md` — architecture stance and layer boundaries
- `SYSTEM_ROADMAP.md` — current priorities, tech debt, future plans
- `AGENTS.md` — agent workflow contract and ownership map

## Quality & Safety
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`
- `docs/SECURITY.md`

## Design & UX
- `docs/DESIGN.md`
- `docs/FRONTEND.md`
- `docs/PRODUCT_SENSE.md`

## Planning
- `docs/PLANS.md` — planning pointer (see `SYSTEM_ROADMAP.md`)

## Generated Artifacts
- `docs/generated/db-schema.md`

## Change Log & History
- `docs/references/change_log/` — chronological change logs for major updates
- `docs/references/REFACTOR_HISTORY.md` — completed refactor phases and outcomes

## Knowledge Base Operating Rules
- `AGENTS.md` stays short and navigational; the system of record lives here in `docs/`.
- Every doc must be indexed with `Doc | Status | Last Verified | Owner`.
- Prefer progressive disclosure: link to deeper sources instead of duplicating rules.
- Keep historical context in change logs rather than ephemeral notes or chat memory.

## Maintenance Rules
- New documentation must live under one of the indexed sections above.
- Indexes must include `Doc | Status | Last Verified | Owner` columns.
- Use relative links; absolute local paths are disallowed.
- Keep docs fresh: update `Last Verified` dates or deprecate stale material.
- Run `uv run python scripts/docs/validate_knowledge_base.py` before merging doc changes.
- Use `uv run python scripts/docs/doc_gardener.py` to surface stale or deprecated docs.
