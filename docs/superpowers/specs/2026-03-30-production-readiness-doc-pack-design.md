# Production Readiness Doc Pack Design

**Date:** 2026-03-30
**Owner:** platform

## Objective
Make production deployment truth explicit without changing runtime behavior. The goal is to remove ambiguity for future engineers/agents by documenting required services, defaults, readiness dependencies, and topology boundaries.

## Scope
- Define production topology (API, web, worker, inference runtime, Redis, SQLite) and required vs optional services.
- Align documented configuration defaults with actual expectations (doc-only, no code changes).
- Clarify readiness/health dependencies and operational commands tied to the topology.
- Reflect doc-level completion in the production readiness checklist.

## Out of Scope
- Runtime behavior changes or enforcement code.
- New product features or UI changes.
- New infra components not already referenced in the roadmap/runbook.

## Design Overview
This is a documentation-only hardening pass. It updates the canonical sources of truth and leaves code behavior unchanged. The changes are structured so that:
- New engineers can answer “what must be running in production” without asking.
- Ops can see how readiness checks relate to missing dependencies.
- Tech debt items can be retired once documentation is aligned.

## Doc Targets & Updates

### 1) `docs/references/operations-runbook.md`
Add a **Production Topology** section that includes:
- Required services: API, web, worker, SQLite, Redis.
- Optional services: inference runtime, vector memory (if used).
- Readiness dependencies: which services cause readiness to degrade.
- Link to readiness command usage and strict mode.

### 2) `docs/references/config-reference.md`
Add or clarify a **Defaults + Required/Optional** table for infra settings:
- Setting name
- Default value
- Required? (yes/no)
- Notes (dependency relationships, e.g., Redis implies worker)

### 3) `SYSTEM_ROADMAP.md`
Add a short bullet in Current Priorities or Completed:
- “Deployment topology and infra assumptions clarified in docs.”

### 4) `docs/exec-plans/active/2026-03-30-production-readiness-checklist.md`
Annotate the checklist items under **Reliability/Operability** and **Deployment Topology** as doc-level complete.

## Acceptance Criteria
- Production topology is explicit with required vs optional services.
- Config defaults and infra dependencies are documented and consistent with runbook.
- Readiness dependencies are documented for degraded conditions.
- Production readiness checklist reflects doc-level completion.

## Risks & Mitigations
- **Risk:** Docs may diverge from actual runtime defaults.
  - **Mitigation:** Keep items doc-only and add a follow-up plan if mismatches are discovered later.

## Rollback Plan
Revert documentation changes only.
