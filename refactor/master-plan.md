# Master Refactor Plan

## Purpose

This is the primary implementation-facing refactor spec inside the `refactor/` package.

It consolidates the decisions from:

- `system-architecture.md`
- `service-contracts.md`
- `safety-spec.md`
- `data-model.md`
- `tech-stack.md`
- `pydanticai-patterns.md`
- `execution-plan.md`

Use this document as the team’s default reference for:

- architecture alignment
- implementation scope
- platform guardrails
- tech choices
- sequencing

## Source of Truth

This file is the source of truth for the `refactor/` package.

Interpretation rule:

- `hackathon-answer.md` is the judge-facing narrative
- `master-plan.md` defines the intended companion architecture and rollout direction
- the remaining files are supporting appendices and must align to this file

Repository-level note:

- the active codebase now already implements the first companion backbone
- top-level docs and implemented code take precedence over any stale aspirational wording in this file

## Challenge Alignment

This plan is aligned to the current hackathon context:

- Singapore-focused consumer health product
- Problem Statement 1 in the SG Innovation Challenge
- localized dietary guidance as the primary product wedge
- `Culture-First, Safety-Always` as the governing product philosophy
- a hackathon-default `local-first` runtime posture, with optional target-aligned infra when needed

## One-Sentence Thesis

Build a `multi-condition, Singapore-native AI health companion` with a `deterministic safety gate`, a `typed longitudinal case snapshot`, a `modular-monolith application spine`, and a `small number of narrow reasoning agents`, while keeping evidence retrieval behind an internal adapter and using bounded worker flows for proactive support.

## Product Boundary

This platform is for consumer health guidance for:

- chronic disease support
- prevention
- awareness
- adherence
- education
- reminders
- caregiver-aware workflows
- Singapore-localized meal guidance
- report and biomarker interpretation support
- voice- and image-assisted daily food decisions

It may:

- educate
- coach
- personalize
- triage for escalation
- guide follow-up actions within policy
- analyze local meals from photos or text
- parse health reports into structured biomarker updates
- provide culturally localized substitutions and portion advice

It must not:

- act as an autonomous clinician
- invent unsupported treatment plans
- persist model guesses as health facts
- let model-generated responses bypass deterministic safety policy

## Non-Negotiable Guardrails

- deterministic policy review runs before any optional model-assisted safety review
- agents propose; they do not authorize
- agents never write durable state directly
- all medically relevant facts use typed write paths
- every user-visible recommendation must be traceable and replayable
- retrieval stays behind `EvidenceRetrievalPort`
- logical service boundaries come before any physical microservice split
- Celery is acceptable only for bounded workflows
- Temporal must be introduced before shipping multi-day or human-in-the-loop care programs that require exact resume semantics

## Existing vs Proposed Scope

The hackathon plan intentionally builds on a codebase that already has meaningful capabilities.

### Already Present in the Current Codebase

- meal analysis and adaptive recommendation flows
- reminder scheduling and medication adherence tracking
- symptom check-ins
- report parsing support
- metrics trend computation
- clinical-card style doctor-facing summaries
- workflow coordination and replay traces
- policy-protected API surfaces
- emotion inference endpoints at Phase 1 integration level
- companion APIs for patient guidance, clinician digest generation, and impact summaries
- a domain/application backbone for `CaseSnapshot`, personalization, engagement, care plans, clinician digest generation, and impact tracking

### Extensions to Existing Capabilities

- make meal analysis more Singapore-localized and culturally realistic
- turn existing reminders into proactive engagement workflows
- turn current report and trend data into a stronger personalization engine
- evolve current clinician summaries into low-burden intervention digests
- evolve current metrics into a clearer impact measurement framework
- use the teammate-owned Chroma retrieval system as an explicit evidence layer

### Net-New Proposed Features

- `Engagement Intelligence Service`
- `Personalization Engine`
- `EvidenceRetrievalPort` over the integrated RAG backend
- `Clinician Copilot Summary Service` with action-oriented digests
- `Impact Measurement Service`
- `Perception and Localization Service` as an explicit multimodal/locale boundary
- emotion-aware coaching behavior on top of existing emotion inference

The plan should therefore be read as:

- not a claim that nothing exists today
- not a greenfield fantasy disconnected from the current repo
- but a consolidation and elevation of existing capabilities into a stronger hackathon and product shape

## Architecture Summary

The platform is organized as:

1. `Experience Gateway`
2. `Perception and Localization Service`
3. `Care Orchestrator`
4. `Profile and Case Service`
5. `Knowledge and Evidence Service`
6. `Engagement Intelligence Service`
7. `Personalization Engine`
8. `Capability Services`
9. `Agent Runtime`
10. `Safety and Policy Service`
11. `Workflow Engine`
12. `Clinician Copilot Summary Service`
13. `Impact Measurement Service`
14. `Evaluation and Audit Service`

### Experience Gateway

Responsibilities:

- auth
- request normalization
- consent checks
- rate limits
- channel adaptation
- streaming

Non-responsibilities:

- medical reasoning
- workflow logic
- policy decisions

### Perception and Localization Service

This is the hackathon-critical input layer.

Responsibilities:

- meal photo understanding
- medicine label and package extraction
- report and PDF parsing
- voice or mixed-language input normalization
- Singapore hawker-food normalization and tagging
- portion-estimation support where feasible

This service converts raw input into typed artifacts such as:

- `MealEvent`
- `MealAnalysisCandidate`
- `BiomarkerUpdate`
- `ReportArtifact`

### Care Orchestrator

This is the central control plane.

Responsibilities:

- load the `CaseSnapshot`
- choose the active interaction or workflow path
- run deterministic capabilities first
- call narrow agents only when needed
- invoke deterministic policy review
- invoke optional `SafetyReviewAgent` only for ambiguity review
- commit events and state transitions
- schedule follow-up work

### Profile and Case Service

Primary source for:

- care profile
- conditions
- medications
- allergies
- goals
- caregiver links
- consent state
- risk state
- stable behavioral preferences

### Knowledge and Evidence Service

Responsibilities:

- retrieve evidence
- package citations
- enforce content versioning
- attach confidence and metadata

Implementation rule:

- the service depends on `EvidenceRetrievalPort`, not directly on Chroma or pgvector

Hackathon adapter:

- `ChromaEvidenceStore`

Future option:

- `PgVectorEvidenceStore`

### Engagement Intelligence Service

This service answers the proactive engagement challenge directly.

Responsibilities:

- detect missed adherence, repeated risky choices, inactivity, and relapse patterns
- choose the right intervention timing
- choose the right intervention intensity
- decide when the tone should be encouragement, accountability, clarification, or escalation
- trigger bounded proactive workflows

Representative outputs:

- `engagement_risk_level`
- `nudge_candidate`
- `follow_up_priority`
- `caregiver_notification_candidate`

### Personalization Engine

This service answers the hyper-personalization challenge directly.

Responsibilities:

- synthesize profile state, meal history, observations, reports, wearable-like inputs, and patient-reported outcomes
- choose which context matters most for this user at this moment
- adapt guidance by condition, medication, culture, language, literacy, and recent behavior
- produce a ranked personalization context for downstream capabilities and agents

Representative inputs:

- `CareProfile`
- `MealEvent`
- `Observation`
- `BiomarkerUpdate`
- `patient_reported_outcome`
- `wearable_summary`

Representative outputs:

- `PersonalizationContext`
- `risk_modifiers`
- `behavioral_modifiers`
- `content_preferences`

### Capability Services

Mostly deterministic services such as:

- symptom extraction
- risk scoring
- adherence scoring
- trend analysis
- recommendation ranking
- education assembly
- reminder planning
- hawker-food normalization
- portion and substitution heuristics
- metabolic impact estimation
- report-to-biomarker extraction post-processing
- adherence trend scoring
- proactive nudge ranking
- clinician-summary drafting inputs

### Agent Runtime

Use a small number of narrow agents:

- `IntentContextAgent`
- `CarePlanningAgent`
- `EvidenceSynthesisAgent`
- `MotivationalSupportAgent`
- optional `SafetyReviewAgent`

Rules:

- typed input and output only
- tool allowlists
- no direct state writes
- no policy ownership
- versioned prompts

### Safety and Policy Service

This is the default safety gate.

Responsibilities:

- red-flag symptom checks
- emergency escalation
- contraindication review
- vulnerable-user protection
- evidence sufficiency checks
- response authorization
- downgrade, replace, or escalate unsafe responses

### Workflow Engine

Manages:

- meal review flows
- report follow-up flows
- reminders
- observation-triggered follow-up
- weekly review
- caregiver branches
- proactive outreach loops
- clinician escalation and summary handoff

Hackathon constraint:

- bounded timers and persisted state are acceptable
- do not ship multi-day or human-in-the-loop workflows on Celery if exact resume or replay semantics are required

### Evaluation and Audit Service

Must capture:

- events
- policy decisions
- agent runs
- evidence references
- workflow timeline
- response trace

### Clinician Copilot Summary Service

This service answers the patient-clinician bridge challenge directly.

Responsibilities:

- convert noisy longitudinal patient activity into concise clinical summaries
- highlight only the highest-value changes and risks
- show why attention is needed now
- package evidence, recent trends, adherence signals, and unresolved concerns
- keep clinician burden low by producing action-oriented summaries rather than raw logs

Representative outputs:

- `ClinicianDigest`
- `InterventionSuggestion`
- `EscalationSummary`

### Impact Measurement Service

This service answers the real-world impact question directly.

Responsibilities:

- compute patient-level outcome metrics
- compute workflow and intervention effectiveness
- compute clinician-efficiency proxies
- track product-level behavioral and biometric change over time
- support before-after and cohort comparisons

Representative outputs:

- `patient_adherence_score`
- `meal_risk_improvement`
- `biometric_trend_delta`
- `clinician_attention_saved_minutes`
- `high_risk_intervention_rate`
- `program_completion_rate`

## End-to-End Request Path

For a normal synchronous interaction:

1. Gateway receives request.
2. Perception and Localization Service converts image, voice, text, or report inputs into typed artifacts.
3. Care Orchestrator loads `CaseSnapshot`.
4. Deterministic preprocessing runs.
5. `IntentContextAgent` classifies intent if needed.
6. `CarePlanningAgent` drafts the next step if needed.
7. `EvidenceSynthesisAgent` and `MotivationalSupportAgent` may assist selectively.
8. Deterministic policy review runs.
9. `SafetyReviewAgent` runs only if deterministic policy marks the case as ambiguous.
10. Orchestrator commits events, state changes, and workflow transitions.
11. Approved response is delivered.

For asynchronous continuation:

1. An event or timer fires.
2. Workflow Engine advances the workflow.
3. Deterministic capabilities evaluate the new state.
4. If needed, narrow agents prepare a proposal.
5. Deterministic policy authorizes the outcome.
6. Orchestrator persists results and triggers delivery.

## Multi-Agent Strategy

### Default Pattern

Use `programmatic hand-off`.

That means:

- code owns routing
- code chooses which agent runs next
- code owns state transitions
- code invokes policy review

### Selective Pattern

Use `agent delegation` only for narrow synthesis subtasks such as:

- care planning to evidence synthesis
- care planning to motivational framing

### Workflow Pattern

Use simple state machines first.

Graph-style orchestration is acceptable only for workflows that are:

- branch-heavy
- resumable
- multi-step
- clearly more complex than a standard interaction

### Avoid

- deep agents
- model-decided routing
- agent-owned state transitions
- agent-owned policy exceptions

## Canonical Data Model

### Core Entities

- `User`
- `Household`
- `CaregiverLink`
- `ConsentRecord`
- `CareProfile`
- `Condition`
- `Medication`
- `Allergy`
- `RiskState`
- `MealEvent`
- `MealAnalysis`
- `FoodItemCandidate`
- `Observation`
- `LabResult`
- `ReportArtifact`
- `BiomarkerUpdate`
- `Interaction`
- `ConversationThread`
- `WorkflowInstance`
- `Reminder`
- `Escalation`
- `EvidenceReference`
- `PolicyDecision`
- `AgentRun`

### Key Read Model

`CaseSnapshot` is the main orchestration read model. It should contain:

- user
- care profile
- conditions
- medications
- goals
- recent observations
- active workflows
- risk state
- behavioral profile
- consent state
- recent meal events
- report-derived biomarker context
- engagement state
- personalization context

### Event Envelope

Every event must include:

- `event_id`
- `event_type`
- `aggregate_type`
- `aggregate_id`
- `occurred_at`
- `causation_id`
- `correlation_id`
- `actor_type`
- `actor_id`
- `schema_version`
- `payload`

### Memory Rules

Separate:

- `health memory`
- `behavioral memory`
- `conversation memory`

Conversation memory must never become durable health fact storage without an explicit typed write path.

## Core Contracts

### Public APIs

Primary endpoints:

- `POST /v1/interactions`
- `POST /v1/meal-analyses`
- `POST /v1/observations`
- `POST /v1/reports/parse`
- `POST /v1/workflows/{workflow_id}/actions`
- `GET /v1/clinician-digests/{user_id}`
- `GET /v1/impact/patients/{user_id}`
- `GET /v1/impact/programs/{program_id}`

### Internal Contracts

Key interfaces:

- `GetCaseSnapshot(user_id, thread_id, intent_hint?)`
- `RetrieveEvidence(task_type, condition_tags, audience, query, limit)`
- `SearchEvidence(query, filters, limit)` via `EvidenceRetrievalPort`
- `BuildPersonalizationContext(case_snapshot, recent_inputs, channel_context)`
- `ScoreEngagementState(user_id, horizon)`
- `RunAgent(agent_name, input, policy_profile, tool_allowlist, schema_version)`
- `ReviewCandidateResponse(candidate_plan, case_snapshot, evidence_items, policy_context)`
- `BuildClinicianDigest(user_id, time_window, trigger_reason)`
- `ComputeImpactMetrics(subject_id, metric_window, metric_profile)`

### Agent Contract Rule

Agents return typed proposals, not final authority.

That applies especially to:

- care planning
- evidence synthesis
- motivational framing
- safety ambiguity review

## Safety Model

### Layered Safety

1. deterministic pre-agent screening
2. candidate generation by capabilities and agents
3. deterministic policy review
4. optional model-assisted ambiguity review
5. final authorization
6. trace and replay

### Decision Outcomes

- `allow`
- `allow_with_downgrade`
- `replace_with_safe_template`
- `require_clinician_escalation`
- `require_emergency_escalation`
- `block`

### Response Modes

- `education_only`
- `guidance`
- `guidance_with_follow_up`
- `monitor_and_check_back`
- `seek_routine_care`
- `seek_urgent_care`
- `seek_emergency_care`
- `blocked`

## Challenge Question Coverage

### 1. Proactive Patient Engagement

Covered by:

- `Engagement Intelligence Service`
- proactive outreach loops in the `Workflow Engine`
- emotion-aware and motivation-aware support through bounded agent use

Target product behaviors:

- detect disengagement before the user drops off
- intervene after risky meal patterns or missed adherence
- choose the right next nudge instead of blasting generic reminders

### 2. Hyper-Personalization of Care

Covered by:

- `Personalization Engine`
- typed multi-source state in `CaseSnapshot`
- report parsing, observations, meal events, and future wearable summaries
- localized cultural and literacy-aware content adaptation

### 3. Bridging the Gap Between Patient and Clinician

Covered by:

- `Clinician Copilot Summary Service`
- action-oriented digests instead of raw logs
- explicit escalation summaries and trend snapshots

### 4. Measuring Real-World Impact

Covered by:

- `Impact Measurement Service`
- patient, workflow, and clinician-efficiency metrics
- traceable intervention and outcome data

## Hackathon Tech Stack

### Use Now

- `Next.js`
- `TypeScript`
- `TanStack Query`
- `FastAPI`
- `Pydantic v2`
- `SQLite` by default
- optional `PostgreSQL` only if the team needs target-aligned shared infra during the hackathon
- `Chroma` behind `EvidenceRetrievalPort`
- `Gemini Flash` or equivalent fast multimodal model for perception
- `Redis`
- `Celery`
- `PydanticAI`
- `MarkItDown` for report parsing
- `Hypothesis` for virtual-patient safety simulation
- explicit Python `Care Orchestrator`
- `pytest`
- `Playwright`
- `Logfire` or OpenTelemetry-aligned tracing

### Why This Stack

- aligns with the current repo
- aligns with the current manifesto and README
- minimizes migration churn
- reuses the teammate-owned Chroma index
- preserves the local-first hackathon posture
- keeps the architecture legible
- preserves a path to stronger workflow durability later

## Minimum Metric Framework

To answer the challenge credibly, the demo should show a metrics layer even if the dataset is small.

### Patient Metrics

- medication adherence rate
- meal-risk score trend
- HbA1c or glucose trend where available
- reminder completion rate
- program completion rate

### Engagement Metrics

- proactive nudge acceptance rate
- response latency to nudges
- re-engagement after drop-off
- sustained weekly activity

### Clinician Metrics

- patients triaged into clinician review
- digest generation latency
- clinician review time saved proxy
- number of escalations with sufficient context

### System Metrics

- safety override rate
- evidence-backed response rate
- low-confidence fallback rate
- end-to-end latency

### Tech Constraints

- do not couple business logic to Chroma APIs directly
- do not run multi-day or human-in-the-loop care programs on Celery if exact resume is required
- do not introduce LangGraph unless workflow complexity proves the need
- do not split into microservices during the hackathon

## Temporal, Celery, and LangGraph Rules

### Celery

Use for:

- reminders
- indexing
- delayed tasks
- bounded follow-up jobs
- batch evaluations

### Temporal

Promote to Temporal before shipping workflows that need:

- multi-day timers
- exact resume semantics
- replayable workflow history as a runtime guarantee
- human-in-the-loop branching

### LangGraph

Optional later.

Use it only if agent workflows become explicitly graph-shaped and resumable. It is not the default orchestrator for the hackathon.

## Phase Plan

### Phase 0: Freeze Architecture

Deliver:

- approved contracts
- glossary
- safety model
- migration inventory
- explicit list of open decisions

### Phase 1: Foundations

Build:

- canonical event envelope
- `CaseSnapshot`
- `PolicyDecision`
- `AgentRun`
- `EvidenceRetrievalPort`
- `ChromaEvidenceStore`
- `Perception and Localization Service`
- `Engagement Intelligence Service`
- `Personalization Engine`
- workflow engine skeleton with persisted workflow state and bounded timers
- agent runtime skeleton
- modular-monolith boundaries for orchestrator, policy, workflow, retrieval, personalization, engagement, clinician summary, and agents

### Phase 2: Safety and Synchronous Spine

Build:

- Care Orchestrator
- multimodal meal/photo/text normalization
- deterministic preprocessing
- personalization context assembly
- Safety and Policy Service
- response authorization pipeline
- replay and tracing
- exact threshold for when Temporal becomes mandatory

Migrate first:

- hawker meal analysis and localized dietary guidance

### Phase 3: Longitudinal Workflows

Build:

- reminders
- observation ingestion
- report parsing follow-up
- weekly review
- caregiver notifications
- engagement scoring
- proactive outreach and relapse detection
- clinician digest generation for high-risk users

If required by target workflows:

- introduce Temporal in this phase

### Phase 4: Knowledge and Personalization

Build:

- curated evidence packs
- content versioning
- ranking
- reading-level adaptation
- disease-specific compositions
- multi-source personalization refinement
- impact dashboard and metric computation

Optional:

- migrate from Chroma to pgvector if the adapter boundary proves insufficient

### Phase 5: Legacy Retirement

Build out and complete:

- removal of prompt-coupled orchestration
- retirement of hidden safety logic
- remaining migration work

## Immediate MVP Cut

If time is tight, implement only:

1. `CaseSnapshot`
2. `EvidenceRetrievalPort` backed by Chroma
3. `Perception and Localization Service` for meal photo/text input
4. `Care Orchestrator`
5. deterministic `Safety and Policy Service`
6. `Personalization Engine` with meal/report/profile fusion
7. `Engagement Intelligence Service` for one proactive nudge path
8. three agents:
   - `IntentContextAgent`
   - `CarePlanningAgent`
   - optional `SafetyReviewAgent`
9. one primary workflow:
   - hawker meal analysis and localized follow-up guidance
10. one clinician-facing digest for a high-risk user
11. one minimal impact dashboard with adherence and meal-risk metrics
12. tracing for:
   - events
   - policy decisions
   - agent runs
   - evidence references

## Open Decisions Before Implementation

- exact Temporal promotion threshold
- model and vendor routing policy
- data residency and compliance assumptions
- SLOs
- cost envelope
- evidence content ownership and curation workflow

## Definition of Done

The hackathon refactor is successful when:

- the team can build against one coherent plan
- the first migrated flow runs through orchestrator, retrieval, policy, and workflow boundaries
- the safety gate is deterministic by default
- the retrieval backend is swappable because it is hidden behind `EvidenceRetrievalPort`
- all recommendations and state changes are traceable
- the architecture remains a modular monolith rather than an accidental distributed system
