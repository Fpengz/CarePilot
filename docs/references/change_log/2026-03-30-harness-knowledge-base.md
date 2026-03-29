# CarePilot Knowledge Base & Harness Alignment Changelog
**Date:** 2026-03-30
**Status:** Completed

## Summary
- Adopted harness-engineering knowledge base conventions as the canonical documentation system.
- Added core beliefs, tech debt tracking, and maintenance rules to keep repository knowledge legible over time.
- Updated templates and tooling references to ensure new contributors can onboard without external context.

## Changes
- **Knowledge Base Rules**: `docs/README.md` now documents system-of-record rules, doc gardening, and validation expectations.
- **Core Beliefs**: Introduced `docs/design-docs/core-beliefs.md` to capture agent-first operating principles.
- **Tech Debt Tracker**: Added `docs/exec-plans/tech-debt-tracker.md` to capture ongoing debt items with ownership and verification dates.
- **Indexes**: Updated design-doc and exec-plan indexes to include new artifacts with freshness metadata.
- **Refactor History**: Recorded the documentation + harness alignment pass for long-term historical context.

## Impact
- New engineers/agents have a durable map of repository knowledge, decisions, and maintenance rules.
- Doc freshness can be validated mechanically and surfaced by the doc-gardener script.
