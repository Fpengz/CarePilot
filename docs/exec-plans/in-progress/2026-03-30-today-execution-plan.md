# Today's Implementation Plan - 2026-03-30

> **Supersedes:** `docs/exec-plans/in-progress/2026-03-27-today-execution-plan.md`

**Goal:** Consolidate unfinished execution items into a single focused plan and add a comprehensive frontend UX critique and checklist.

**Priorities (Today):**
1. Carry over unfinished production readiness workstreams.
2. Carry over unfinished hardening + DB/API refactor items.
3. Execute frontend UX improvements guided by the critique checklist.

---

## Carry-over: Production Readiness Checklist (2026-03-30)
Source: `docs/exec-plans/active/2026-03-30-production-readiness-checklist.md`

### Reliability & Operability
- [ ] Ensure readiness checks cover API + workers + inference runtime.
- [ ] Validate predictable worker scheduling behavior under load.

### Observability
- [ ] Ensure request ID + correlation ID are available across API and workers.
- [ ] Verify workflow traces are accessible for primary journeys (meals, meds, chat).
- [ ] Standardize incident triage steps for degraded readiness or worker failures.

### Data Integrity
- [ ] Confirm SQLModel migrations cover all normalized tables in production paths.
- [ ] Verify projections replay path for event timeline rebuilds.
- [ ] Document rollback / recovery for migration or schema failures.

### Messaging Readiness
- [ ] Complete inbound message processing (webhooks + normalization).
- [ ] Stabilize attachment handling (images/audio) across channels.
- [ ] Verify worker + scheduler are required for reminder dispatch.

### Clinical Safety & Guardrails
- [ ] Strengthen clinician summaries for risk, adherence, and safety triage.
- [ ] Validate safety guardrails for user-facing recommendations.
- [ ] Ensure policy enforcement modes and role mappings are documented.

### E2E Validation
- [ ] Playwright coverage for core flows (Meal → Meds → Reminders → Chat).
- [ ] Run comprehensive gate before release (`uv run python scripts/cli.py test comprehensive`).

---

## Carry-over: Production Hardening Design (2026-03-26)
Source: `docs/exec-plans/active/2026-03-26-production-ready-hardening-design.md`

- [ ] Database hardening (schema, indexing, backup/disaster recovery).
- [ ] Event-driven system hardening (schemas, retries, dead-letter handling).
- [ ] Backend worker resilience (queueing, monitoring, graceful shutdown, scaling).
- [ ] Context management & pruning for agents and multi-modal memory.
- [ ] Data pipelines & evaluation hardening integrated into CI/CD.
- [ ] Harness engineering upgrades for local dev + testing reliability.

---

## Carry-over: DB/API Refactor Design (2026-03-27)
Source: `docs/exec-plans/active/2026-03-27-db-api-refactor-design.md`

- [ ] Normalize `UserProfileRecord` JSON fields into relational tables.
- [ ] Refine medication + reminder data flow (clear ownership and FK enforcement).
- [ ] Audit `WorkflowTimelineEventRecord` payloads and extract structured tables.
- [ ] Normalize `MealRecord` + `BiomarkerReading` data where queried frequently.
- [ ] Remove legacy ORM definitions outside SQLModel.
- [ ] Optimize API data pipelines (lean DTOs, pagination, snapshot granularity).
- [ ] Update validation/migration strategy (tests, perf, observability).

---

## Frontend UX Critique + Checklist (Full)

### Anti-Patterns Verdict (AI‑Slop Test)
**Fail.** Repeated glass cards, micro‑labels, generic typography (Inter), decorative sparklines, and uniform spacing flatten hierarchy and feel templated.

### Executive Summary
**Top issues:**
1. Hierarchy flattening from repeated containers and micro‑labels.
2. Typography compression (titles and body too close in scale/weight).
3. Contrast drift on tinted surfaces (risk in light/dark).
4. Mobile density and touch-target risks.

### Detailed Findings (by severity)
**Critical**
- Hierarchy fails under load; primary signal is not obvious.

**High**
- Typography hierarchy too narrow.
- Micro‑label overload (uppercase everywhere).
- Contrast drift on tinted surfaces.

**Medium**
- Card grid fatigue; weak visual rhythm.
- Charts lack clear story headlines.

**Low**
- Typography monotony (weights + sizes too uniform).
- Spacing uniformity across sections.

### Polish Checklist (Actionable)
**Typography**
- [ ] Reduce uppercase micro‑labels to section headers only.
- [ ] Increase contrast between H1/H2/body.
- [ ] Add one stronger font weight for emphasis.
- [ ] Limit to 2 typography scales per screen (title + body).

**Layout & Rhythm**
- [ ] Introduce at least one non‑card section per page.
- [ ] Vary spacing: one dense cluster + one airy zone per screen.
- [ ] Ensure primary section is visually dominant.

**Color & Contrast**
- [ ] Replace gray‑on‑tint text with proper tokenized contrast.
- [ ] Define one primary accent for alerts/actions.
- [ ] Verify dark‑mode contrast at AA minimum.

**Charts & Data**
- [ ] Add a one‑line story headline above each major chart.
- [ ] Remove decorative sparklines or make them interactive.

**UX & Responsiveness**
- [ ] Ensure 44x44 touch targets on mobile.
- [ ] Avoid 3‑column grids below ~1024px.
- [ ] Test content density at 375px width.

---

## Notes
- Older plan files are superseded but retained for historical context.
- This file is the single execution source of truth for 2026‑03‑30.
