# Today's Implementation Plan - 2026-04-01

**Goal:** Complete unfinished stability, versioning, and production-readiness tasks from previous days.

## 1. Versioning & Changelog Automation
Carry-over from `2026-03-31-versioning-automation.md`.
- [x] Initialize `CHANGELOG.md` at root following "Keep a Changelog" format.
- [x] Implement `scripts/cli/commands/version.py` with `status`, `patch`, `minor`, `major` commands.
- [x] Update `scripts/cli.py` to register the version command.

## 2. Harness Engineering & Repository Health (NEW)
Inspired by Anthropic Engineering principles.
- [x] Consolidate naming standards and write into `AGENTS.md` as hard rules.
- [x] Integrate backend and frontend tests into `.pre-commit-config.yaml`.
- [x] Implement `scripts/housekeeping.py` for overnight repository maintenance (now with stale plan **promotion** logic).
- [x] Add `housekeeping` target to `Makefile`.
- [x] Document housekeeping and validation rules in `AGENTS.md`.

## 3. Stability Foundation (Observability Pillar)
Carry-over from `2026-03-31-phase-1-stability-foundation-design.md`.
- [x] Refactor `src/care_pilot/platform/observability/setup.py` to use a unified `setup_observability` function.
- [x] Mass-replace `print()` statements with `logfire.info()` or appropriate logging levels.
- [x] Ensure `logfire` instruments FastAPI and SQLModel engine.

## 4. Production Readiness & Hardening
Carry-over from `2026-03-30-production-readiness-checklist.md`.
- [x] Verify `request_id` and `correlation_id` are correctly propagated in background workers.
- [ ] Verify SQLModel migrations cover all normalized tables.
- [x] Run `uv run python scripts/cli.py test comprehensive` to verify overall system stability.

## 5. Frontend UX Final Polish
Carry-over from `2026-03-30-frontend-un-slop-implementation.md`.
- [x] Verify 44x44 touch targets for mobile actions.
- [x] Final responsive pass for Dashboard and Chat pages.


## Status Summary (2026-04-01)
- **Dashboard Simplification**: Completed (unused components deleted, imports cleaned).
- **Relational Profile Migration**: Completed (User profiles normalized).
- **Versioning**: Not started.
- **Unified Observability**: Partially completed (setup.py exists but needs refinement).
