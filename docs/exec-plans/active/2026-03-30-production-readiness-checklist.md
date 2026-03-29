# Production Readiness Checklist (2026-03-30)

## Purpose
Define the minimum checklist and milestones required to take CarePilot from the current state to a customer-facing, production-ready release. This checklist is sourced from the existing roadmap, tech-debt tracker, and ops runbook.

## Scope
- Production hardening for API, workers, and inference runtime.
- Operational readiness (health checks, observability, incident paths).
- Messaging readiness and multi-channel stability.
- Clinical safety guardrails and clinician-facing outputs.

## Out of Scope
- New product features beyond the current roadmap.
- Major UI/UX redesigns.
- New data source integrations not already in the roadmap.

---

## Milestones & Checklists

### 1) Reliability & Operability
- [ ] Document required vs optional infra (Redis, vector memory, worker queues) in config and runbook.
- [ ] Align runtime configuration defaults with the config reference.
- [ ] Ensure readiness checks cover API + workers + inference runtime.
- [ ] Validate predictable worker scheduling behavior under load.

### 2) Observability
- [ ] Ensure request ID + correlation ID are available across API and workers.
- [ ] Verify workflow traces are accessible for primary journeys (meals, meds, chat).
- [ ] Standardize incident triage steps for degraded readiness or worker failures.

### 3) Data Integrity
- [ ] Confirm SQLModel migrations cover all normalized tables in production paths.
- [ ] Verify projections replay path for event timeline rebuilds.
- [ ] Document rollback / recovery for migration or schema failures.

### 4) Messaging Readiness
- [ ] Complete inbound message processing (webhooks + normalization).
- [ ] Stabilize attachment handling (images/audio) across channels.
- [ ] Verify worker + scheduler are required for reminder dispatch.

### 5) Clinical Safety & Guardrails
- [ ] Strengthen clinician summaries for risk, adherence, and safety triage.
- [ ] Validate safety guardrails for user-facing recommendations.
- [ ] Ensure policy enforcement modes and role mappings are documented.

### 6) Deployment Topology
- [ ] Define production topology for API, web, worker, inference runtime.
- [ ] Document required environment variables and runtime dependencies.
- [ ] Ensure infra control commands (`infra up/down/status`) map to the production topology.

### 7) E2E Validation
- [ ] Playwright coverage for core flows (Meal → Meds → Reminders → Chat).
- [ ] Run comprehensive gate before release (`uv run python scripts/cli.py test comprehensive`).

---

## Ownership
- Primary owner: platform
- Contributors: agent, product, web (as needed)

## Sources
- `SYSTEM_ROADMAP.md` (current priorities + known tech debt)
- `docs/exec-plans/tech-debt-tracker.md`
- `docs/references/operations-runbook.md`
