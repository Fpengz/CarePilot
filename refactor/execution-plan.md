# Execution Plan

## Purpose

Define a phased path from the current repository to the clean-slate target architecture.

This plan assumes backward compatibility is not a design constraint, but controlled migration risk still matters.

## Strategy

Do not refactor the current monolith in place until boundaries are clear.

Instead:

1. establish the target contracts
2. build the new platform seams
3. migrate selected flows incrementally
4. retire old orchestration once parity and safety targets are met

## Phase 0: Alignment and Design Freeze

Deliverables:

- architecture review sign-off
- domain glossary
- service boundary approval
- safety model approval
- migration inventory of current code
- explicit current-vs-proposed feature map

Exit criteria:

- `refactor/` docs approved by engineering leads
- critical open questions tracked explicitly
- existing vs net-new scope agreed

## Phase 1: Foundations

Workstreams:

- create canonical event envelope
- define core domain schemas
- build case snapshot read model
- introduce policy decision artifact model
- wrap the teammate-owned Chroma index behind an internal retrieval adapter
- stand up workflow engine skeleton with persisted workflow state and bounded timer support
- stand up agent runtime skeleton with structured I/O

Expected output:

- target platform skeleton exists as an extension-friendly modular monolith
- no user-facing migration yet

Exit criteria:

- core schemas versioned
- retrieval backend hidden behind `EvidenceRetrievalPort`
- workflow and agent runtimes callable in isolation
- policy decision records persist cleanly
- existing capability reuse points documented

## Phase 2: Safety and Orchestration Spine

Workstreams:

- implement Care Orchestrator
- implement Safety and Policy Service
- implement deterministic preprocessing capabilities
- implement evidence retrieval contract
- implement personalization context assembly
- implement one proactive engagement scoring loop
- define response authorization pipeline
- define the workflow durability threshold that forces migration from Celery to Temporal

First migrated flow:

- hawker meal analysis and localized dietary guidance

Reason:

- highest hackathon value
- directly reflects the current challenge framing and manifesto
- exercises perception, localization, safety, evidence, and agent coordination together

Exit criteria:

- new meal-guidance flow works end to end
- safety traces and replay exist
- policy decisions are explicit

## Phase 3: Longitudinal Support Flows

Workstreams:

- reminders and adherence workflows
- observation ingestion
- weekly review workflow
- caregiver-aware notification pathways
- engagement scoring
- introduce `Temporal` in this phase if any target workflow requires multi-day timers, exact resume semantics, or human-in-the-loop branching

Exit criteria:

- observation-driven workflows run durably on the chosen engine, with the durability decision documented
- reminder loop no longer depends on legacy orchestration
- user timeline is reconstructible from events

## Phase 4: Knowledge and Personalization Expansion

Workstreams:

- curated evidence packs
- content versioning
- optional migration from Chroma to pgvector if justified by platform needs
- recommendation ranking
- reading-level adaptation
- disease-specific experience composition
- clinician summary generation
- impact metric computation and dashboarding

Exit criteria:

- evidence-backed education flows use new retrieval service
- specialist product experiences are composed from shared capabilities

## Phase 5: Legacy Retirement

Workstreams:

- remove prompt-coupled orchestration paths
- retire hidden safety logic in legacy services
- migrate remaining flows
- archive or delete obsolete adapters

Exit criteria:

- all user-visible care flows route through new orchestrator
- legacy orchestration is off by default
- production incident review works from new traces only

## Team Structure by Workstream

### Workstream A: Core Platform

Ownership:

- event model
- orchestrator
- workflow engine
- shared contracts

### Workstream B: Safety and Policy

Ownership:

- safety service
- escalation logic
- replay harness
- policy versioning

### Workstream C: Data and Knowledge

Ownership:

- read models
- evidence store
- retrieval interfaces
- migration tooling

### Workstream D: Agent Runtime

Ownership:

- structured model execution
- prompt versioning
- tool governance
- run trace artifacts

### Workstream E: Experience Migration

Ownership:

- gateway integration
- frontend contract updates
- user-facing workflow adoption

## Initial Engineering Backlog

Highest-priority engineering tickets:

1. Define canonical `CaseSnapshot` schema.
2. Define canonical `PolicyDecision` schema.
3. Define canonical `AgentRun` schema.
4. Build event envelope and event publishing library.
5. Build meal-photo or meal-text perception normalization for Singapore-localized dishes.
6. Build orchestration pipeline for one synchronous meal-guidance path.
7. Build safety review pipeline with typed decision output.
8. Build one durable workflow: meal analysis follow-up.
9. Build replay harness for safety and orchestration traces.

## Platform Guardrails

- deterministic policy review runs before any optional model-assisted safety review
- `SafetyReviewAgent` is an ambiguity helper, not the default safety gate
- `Celery` is acceptable only for bounded workflows; promote `Temporal` before multi-day or human-in-the-loop programs ship
- retrieval remains behind `EvidenceRetrievalPort` regardless of Chroma or pgvector choice
- logical service boundaries may ship inside a modular monolith before any runtime split
- the first user-visible migrated flow must serve the hackathon wedge: localized dietary guidance, not a generic symptom assistant
- the hackathon demo must include one proactive engagement behavior, one clinician digest, and one impact metric view

## Migration Rules

- new flows must not bypass the policy layer
- new agent usage must use structured input and output
- no new hidden prompt logic in transport or UI layers
- user facts migrate through typed write paths only
- every migrated flow must emit traceable events

## Validation Strategy

### Design Validation

- schema review
- sequence diagram review
- failure-mode review
- safety policy review

### Engineering Validation

- contract tests
- workflow tests
- replay tests
- red-flag scenario tests
- agent output schema validation

### Operational Validation

- synthetic traffic
- shadow mode on selected flows
- incident drill for escalation behavior
- observability dashboard review

## Risks

### Risk: Architecture Drift

Mitigation:

- keep contracts versioned
- require architecture review for boundary violations

### Risk: Agent Sprawl

Mitigation:

- require justification for every new agent
- default to deterministic services

### Risk: Safety Fragmentation

Mitigation:

- centralize policy service ownership
- prohibit agent-owned policy exceptions

### Risk: Migration Stall

Mitigation:

- migrate one high-value workflow at a time
- define retirement criteria early

## Definition of Done for the Refactor

The refactor is complete when:

- all high-impact user flows use the new Care Orchestrator
- safety decisions are explicit persisted artifacts
- longitudinal workflows are durable and replayable
- agent runs are typed and independently auditable
- specialist user experiences are composed from shared capabilities
- legacy orchestration paths are retired
