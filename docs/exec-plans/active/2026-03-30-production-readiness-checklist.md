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
- [x] Document required vs optional infra (Redis, vector memory, worker queues) in config and runbook. (doc-level complete)
- [x] Align runtime configuration defaults with the config reference. (doc-level complete)
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
- [x] Define production topology for API, web, worker, inference runtime. (doc-level complete)
- [x] Document required environment variables and runtime dependencies. (doc-level complete)
- [x] Ensure infra control commands (`infra up/down/status`) map to the production topology. (doc-level complete)

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

---

## Frontend UX Critique + Checklist (Full)

### Anti-Patterns Verdict (AI-Slop Test)
**Fail.** Repeated glass cards, micro-labels, generic typography (Inter), decorative sparklines, and uniform spacing flatten hierarchy and feel templated.

### Executive Summary
**Top issues:**
1. Hierarchy flattening from repeated containers and micro-labels.
2. Typography compression (titles and body too close in scale/weight).
3. Contrast drift on tinted surfaces (risk in light/dark).
4. Mobile density and touch-target risks.

### Detailed Findings (by severity)
**Critical**
- Hierarchy fails under load; primary signal is not obvious.

**High**
- Typography hierarchy too narrow.
- Micro-label overload (uppercase everywhere).
- Contrast drift on tinted surfaces.

**Medium**
- Card grid fatigue; weak visual rhythm.
- Charts lack clear story headlines.

**Low**
- Typography monotony (weights + sizes too uniform).
- Spacing uniformity across sections.

### Polish Checklist (Actionable)
**Typography**
- [ ] Reduce uppercase micro-labels to section headers only.
- [ ] Increase contrast between H1/H2/body.
- [ ] Add one stronger font weight for emphasis.
- [ ] Limit to 2 typography scales per screen (title + body).

**Layout & Rhythm**
- [ ] Introduce at least one non-card section per page.
- [ ] Vary spacing: one dense cluster + one airy zone per screen.
- [ ] Ensure primary section is visually dominant.

**Color & Contrast**
- [ ] Replace gray-on-tint text with proper tokenized contrast.
- [ ] Define one primary accent for alerts/actions.
- [ ] Verify dark-mode contrast at AA minimum.

**Charts & Data**
- [ ] Add a one-line story headline above each major chart.
- [ ] Remove decorative sparklines or make them interactive.

**UX & Responsiveness**
- [ ] Ensure 44x44 touch targets on mobile.
- [ ] Avoid 3-column grids below ~1024px.
- [ ] Test content density at 375px width.
