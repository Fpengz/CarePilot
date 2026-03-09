# System Roadmap

## Purpose
This file is the active root roadmap for the hackathon branch.

The current objective is to turn the repository from a strong set of health-support features into a coherent AI health companion with:
- proactive patient engagement
- multi-source personalization
- clinician-facing summaries
- measurable impact tracking

## Current Phase
### Phase 1: Companion Backbone
Delivered in the current branch:
- `domain/care` contracts
- application modules for case snapshot, personalization, engagement, care plans, clinician digest, and impact
- companion APIs:
  - `GET /api/v1/companion/today`
  - `POST /api/v1/companion/interactions`
  - `GET /api/v1/clinician/digest`
  - `GET /api/v1/impact/summary`

### Phase 2: Interaction Intelligence
Delivered in the current branch:
- application-layer companion orchestration in `application/interactions`
- explicit evidence retrieval boundary in `application/evidence` with deterministic adapter in `infrastructure/evidence`
- deterministic safety review in `application/safety`
- interaction-type-specific planning for `chat`, `meal_review`, `check_in`, `report_follow_up`, and `adherence_follow_up`
- clinician digests with `why now`, priority, interventions attempted, and citations
- impact summaries with baseline/comparison windows and delta-oriented metrics
- companion-first web pages for `/companion`, `/clinician-digest`, and `/impact`

## Next Phases
### Phase 3: Proactive Engagement Expansion
- promote reminder and adherence workflows into explicit proactive outreach triggers
- add inactivity, repeated risky meal, and worsening symptom triggers
- persist intervention outcomes for replay and evaluation

### Phase 4: Evidence and Reasoning Upgrade
- replace deterministic evidence packs with the full integrated retrieval backend behind the existing evidence port
- add richer provenance, condition-pack coverage, and citation quality checks
- tighten condition-pack extensibility for multi-condition support

### Phase 5: Scale-Later Runtime
- strengthen PostgreSQL and Redis as the target-aligned local stack
- evaluate workflow durability needs before introducing heavier orchestration
- preserve the modular monolith until runtime split becomes justified

## Hackathon Success Criteria
- Patient-facing demo shows proactive guidance rather than passive CRUD.
- Personalization clearly uses more than one source of truth.
- Clinician digest shows what changed, why it matters, and what to do next.
- Impact summary shows adherence, engagement, or risk metrics changing over time.

## Related References
- `README.md`
- `ARCHITECTURE.md`
- `docs/feature-audit.md`
- `docs/roadmap-v1.md`
