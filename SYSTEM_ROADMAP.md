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
- modular `domain` and `application` backbone for companion workflows
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
- strengthen runtime topology validation for the SQLite plus optional Redis path
- improve observability and safety behavior on real request paths before adding more surface area
- completed architecture refactor: deleted services/, runtime/, and models lazy-export shim; consolidated observability; added SafetyPort and typed agent schema contracts

## Delivered phases

### Phase 1: Companion backbone
Delivered:
- `domain/care` and related application modules for case snapshot, personalization, engagement, care plans, clinician digest, and impact
- typed companion APIs:
  - `GET /api/v1/companion/today`
  - `POST /api/v1/companion/interactions`
  - `GET /api/v1/clinician/digest`
  - `GET /api/v1/impact/summary`

### Phase 2: Interaction intelligence
Delivered:
- application-layer interaction orchestration
- deterministic evidence retrieval boundary and adapter
- deterministic safety review before response serialization
- interaction-type-specific planning for `chat`, `meal_review`, `check_in`, `report_follow_up`, and `adherence_follow_up`
- clinician digests with priority, change summary, interventions attempted, and citations
- impact summaries with baseline/comparison windows and delta-oriented metrics
- companion-first web pages for `/companion`, `/clinician-digest`, and `/impact`

## Current feature status
- `meal analysis and weekly nutrition patterns`: complete baseline
- `recommendation agent and substitution flows`: complete baseline, still being hardened
- `medication tracking and reminder automation`: complete baseline
- `symptom check-ins and report context`: complete baseline
- `clinical cards and metric trends`: complete baseline
- `emotion inference API`: implemented behind feature flags
- `community/caregiver monitoring`: complete baseline for current care flows

## Next phases

### Phase 3: Proactive engagement
- turn reminder and adherence signals into explicit proactive outreach triggers
- add inactivity, repeated risky meal, and worsening symptom triggers
- persist intervention outcomes for replay and evaluation

### Phase 4: Evidence and reasoning upgrade
- replace deterministic evidence packs with a fuller retrieval backend behind the existing evidence port
- improve provenance, citation quality, and multi-condition support
- harden prompt assembly and agent contract consistency where agents are still used

### Phase 5: Runtime hardening
- strengthen the SQLite-first topology as the standard target-aligned stack
- improve observability, readiness, and failure recovery around worker and provider flows
- keep the modular monolith intact until runtime split is justified by real constraints

## Execution posture
- fold new capabilities behind the existing modular-monolith boundaries instead of creating parallel systems
- prefer incremental migration of important flows over clean-slate rewrites
- retire duplicate architecture or planning artifacts once their useful content has been absorbed into canonical docs and code

## Success criteria for this branch
- the demo shows proactive guidance rather than passive CRUD
- personalization clearly uses more than one source of truth
- clinician output explains what changed, why it matters, and what to do next
- impact output shows measured change over time

## Related references
- `README.md`
- `ARCHITECTURE.md`
- `docs/hackathon-answer.md`
- `docs/meal-analysis-agents.md`
- `docs/operations-runbook.md`
