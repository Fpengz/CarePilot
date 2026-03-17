# System Roadmap

## Purpose
This is the single roadmap and status file for the hackathon branch. It replaces the older split between roadmap and capability-audit summaries.

Current objective:
- proactive patient engagement
- multi-source personalization
- clinician-facing summaries
- measurable health impact

## Current maturity
Implemented baseline:
- FastAPI API with auth, policy, typed contracts, and workflow trace support
- Next.js frontend with companion-facing routes and typed API integration
- feature-first `features/` backbone for companion workflows
- deterministic evidence and safety boundaries in the companion flow
- companion APIs for today view, interactions, clinician digest, and impact summary
- meal analysis with bounded perception and deterministic canonical-food enrichment
- recommendations, reminders, medications, symptoms, reports, metrics, and clinical cards
- SQLite default persistence with optional Redis-backed coordination path
- external worker runtime for reminders and outbox-style async processing

Not yet fully productized:
- SQLite and optional Redis as the standard hackathon runtime
- full retrieval and indexing pipeline behind the evidence boundary
- more proactive intervention triggers and replay-oriented evaluation
- richer offline evaluation and production-hardening around agent quality

Current baseline versus target direction:
- already present: meals, recommendations, reminders, medications, symptoms, reports, trends, clinical cards, workflow traces, policy-protected APIs, and feature-flagged emotion inference
- still maturing: proactive engagement logic, evidence-backed retrieval quality, richer clinician-facing summarization, and measured impact loops that are explicit enough for pilots

Current hardening emphasis:
- stabilize typed API contracts and frontend error handling
- reduce opaque orchestration and broad service-locator patterns
- establish `features/`, `agent/`, `platform/`, `core/`, and `core/contracts/api/` as the canonical backend surfaces
- completed architecture refactor: removed legacy layered packages, relocated API schemas to core contracts, and stabilized the persistence layer.
- finalized feature-first modular monolith structure with job-based service naming (e.g., `meal_service.py`, `medication_management.py`).

## Delivered phases

### Phase 1: Companion backbone
Delivered:
- `features/companion/*` modules for case snapshot, personalization, engagement, care plans, clinician digest, and impact
- typed companion APIs:
  - `GET /api/v1/companion/today`
  - `POST /api/v1/companion/interactions`
  - `GET /api/v1/clinician/digest`
  - `GET /api/v1/impact/summary`

### Phase 2: Structural hardening and contracts
Delivered:
- relocation of all API schemas to `src/care_pilot/core/contracts/api/`
- decoupling of feature logic from the API app layer
- extraction of cross-feature orchestration to API services
- stabilization of the SQLite persistence layer with a central bootstrap mechanism
- resolution of circular import patterns across domain and workflow models

### Phase 3: Proactive engagement
Delivered:
- turn reminder and adherence signals into explicit proactive outreach triggers
- add inactivity, repeated risky meal, and worsening symptom triggers
- persist intervention outcomes for replay and evaluation

### Phase 4: Structural Hardening and Feature-First Refactor
Delivered:
- Renamed 21+ files to follow job-based naming conventions (e.g., `service.py` -> `meal_service.py`).
- Established the "feature-first modular monolith" as the canonical architecture.
- Refactored `src/care_pilot/features/` to ensure strict ownership and bounded contexts.
- Consolidated agent-layer logic into `src/care_pilot/agent/`.
- Verified system-wide stability after the structural reorganization.

### Phase 5: Documentation and Submission Prep (ACTIVE)
- Update all project documentation (`*.md` files) to reflect the finalized file structure.
- Replace generic file references with specific job-based names across the codebase and docs.
- Ensure ARCHITECTURE.md matches the current reality of the `src/` folder.
- Fix broken links and verify consistency across all documentation.
- Finalize the README and submission materials for the hackathon.

## Related references
- `README.md`
- `ARCHITECTURE.md`
- `docs/developer-guide.md`
- `docs/meal-analysis-agents.md`
- `docs/operations-runbook.md`
