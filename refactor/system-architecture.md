# System Architecture

## Goal

Design a Singapore-focused consumer health guidance platform whose primary hackathon value is localized dietary guidance, while remaining extensible to chronic disease prevention, management, and future care-adjacent workflows.

The platform should optimize for:

- safety
- longitudinal support
- explainability
- reuse
- operational visibility
- ability to add new conditions without forking the architecture

## Product Boundary

This platform is for consumer health guidance.

It may:

- educate
- coach
- personalize
- remind
- triage for escalation
- help users form healthier habits
- support caregiver and household workflows
- analyze meals from photos, voice, and text
- parse reports into biomarker-aware guidance
- localize advice for Singapore hawker and kopi-shop contexts

It must not:

- behave like an autonomous clinician
- create unsupported treatment instructions
- persist model guesses as medical facts
- bypass safety policy for better UX

## Architectural Thesis

The correct primary abstraction is `policy-governed capabilities`, not `agent`.

The correct platform stack is:

1. `experiences`
2. `gateway`
3. `perception and localization`
4. `care orchestration`
5. `engagement intelligence`
6. `personalization`
7. `capabilities`
8. `agent runtime`
9. `safety and policy`
10. `workflow engine`
11. `clinician summary`
12. `impact measurement`
13. `data and evaluation`

Specialist experiences such as `Diabetes Coach` or `Prevention Coach` are product compositions on top of this shared platform.

## Core Principles

### Deterministic Before Generative

If a task can be done by:

- rules
- scoring
- retrieval
- ranking
- templates
- state machines

then it should not be owned by an agent.

### Typed State Over Chat Memory

The source of truth is:

- structured user and case state
- observations
- workflow state
- policy decisions
- event history

Chat history is only a context aid.

### Safety as an Independent Layer

Safety must be able to veto, downgrade, or escalate any high-impact response without relying on the proposing agent.

### Longitudinal by Design

The platform must support multi-day and multi-month journeys, not just reactive chat turns.

### Explainability as a Runtime Requirement

Every response should be traceable to:

- state snapshot
- retrieved evidence
- capability results
- agent outputs
- safety decisions

## Platform Services

### 1. Experience Gateway

Responsibilities:

- auth
- rate limiting
- consent verification
- request normalization
- channel adaptation
- response streaming
- request and correlation IDs

Non-responsibilities:

- medical reasoning
- workflow logic
- safety decisions

### 2. Care Orchestrator

This is the central execution coordinator.

Responsibilities:

- load the case snapshot
- select the active workflow
- call deterministic capabilities
- invoke agents when needed
- merge candidate outputs
- call safety review
- commit state transitions
- launch asynchronous follow-up work

This service is the one place where synchronous user interaction and longitudinal workflow state meet.

### Perception and Localization Service

This is the hackathon-specific differentiator layer.

Responsibilities:

- multimodal ingest normalization for image, text, voice, and document inputs
- meal photo understanding
- local food-name normalization
- portion-estimation support
- OCR and report extraction support
- conversion of raw inputs into typed artifacts before reasoning

Representative outputs:

- `MealEvent`
- `MealAnalysisCandidate`
- `ReportArtifact`
- `BiomarkerUpdate`

### 3. Profile and Case Service

Responsibilities:

- user profile
- household and caregiver links
- conditions
- medications
- goals
- allergies
- consent state
- risk tier
- stable behavioral preferences

This is the primary read model for user context assembly.

### 4. Knowledge and Evidence Service

Responsibilities:

- curated medical and education content
- content versioning
- retrieval
- citation packaging
- reading-level adaptation metadata
- evidence confidence metadata

It should return structured evidence objects rather than raw documents.

It should depend on an internal `EvidenceRetrievalPort`, not on a specific vector store directly.

Hackathon implementation:

- `ChromaEvidenceStore` backed by the teammate-owned Chroma collection

Scale-later options:

- `PgVectorEvidenceStore`
- dual-read or dual-write transition if the team later migrates away from Chroma

### 5. Capability Services

Representative capabilities:

- hawker-food normalization
- localized substitution heuristics
- metabolic impact estimation
- symptom extraction
- risk stratification
- adherence scoring
- trend analysis
- recommendation ranking
- education assembly
- reminder planning
- check-in generation
- care navigation suggestions

These are reusable and mostly deterministic.

### Engagement Intelligence Service

Responsibilities:

- detect disengagement and relapse patterns
- choose proactive follow-up timing and intensity
- rank nudge candidates
- prepare bounded proactive outreach triggers

### Personalization Engine

Responsibilities:

- synthesize profile, meal, biomarker, report, patient-reported, and future wearable context
- select the most relevant context for each decision
- adapt guidance by condition, culture, literacy, language, and recent behavior

### 6. Agent Runtime

The agent runtime executes narrow reasoning jobs with strict contracts.

Initial agents:

- `IntentContextAgent`
- `CarePlanningAgent`
- `EvidenceSynthesisAgent`
- `MotivationalSupportAgent`
- optional `SafetyReviewAgent` for ambiguity review only

Rules:

- structured input only
- structured output only
- tool allowlists per agent
- no direct writes to durable state
- versioned prompts and configs

### 7. Safety and Policy Service

Responsibilities:

- red-flag symptom checks
- emergency escalation
- contraindication rules
- vulnerable-user protection
- evidence sufficiency checks
- response authorization
- unsafe-advice downgrade or replacement

This service must be deterministic where possible and model-assisted only where ambiguity remains.

### 8. Workflow Engine

Responsibilities:

- durable workflow state
- timers and retries
- pauses and resumptions
- reminder schedules
- escalation follow-up
- care program sequencing

Representative workflows:

- onboarding
- baseline risk capture
- meal analysis and meal follow-up
- symptom triage
- report follow-up
- weekly review
- medication adherence loop
- prevention program

### 9. Evaluation and Audit Service

Responsibilities:

- decision trace storage
- policy replay
- model comparison
- red-team evaluation
- drift detection
- incident investigation support

### Clinician Summary Service

Responsibilities:

- generate concise action-oriented patient summaries
- highlight trend changes, adherence issues, and risk flags
- reduce clinician reading burden

### Impact Measurement Service

Responsibilities:

- compute patient outcome metrics
- compute workflow effectiveness
- compute clinician-efficiency proxies
- support before-after evaluation

## Runtime Topology

### Edge/API Tier

Optimized for:

- ingress
- auth
- channel handling
- streaming

### Orchestration Tier

Optimized for:

- low-latency synchronous care interactions
- state assembly
- capability fanout
- agent coordination

### Workflow Tier

Optimized for:

- delayed jobs
- timers
- retries
- multi-step journeys

### Agent Tier

Optimized for:

- structured inference
- agent isolation
- cost controls
- tool governance

### Data Tier

Optimized for:

- operational durability
- event history
- caching
- queues and locks
- retrieval indexes

The retrieval index may be implemented by Chroma for the hackathon, but the rest of the platform should only depend on the evidence service and retrieval port.

### Safety/Eval Tier

Optimized for:

- policy execution
- output validation
- audit
- replay

## End-to-End Interaction Model

### Synchronous Path

1. User sends a message or structured input.
2. Gateway authenticates and normalizes the request.
3. Care Orchestrator loads the case snapshot.
4. Deterministic preprocessing runs.
5. Relevant agents produce typed proposals.
6. Orchestrator merges proposals into a candidate plan.
7. Safety and Policy Service authorizes, downgrades, or escalates.
8. State and events are committed.
9. Approved response is delivered.

### Asynchronous Path

1. A timer, missed reminder, new observation, or risk change emits an event.
2. Workflow Engine advances the relevant care program.
3. Capability services evaluate the state change.
4. If needed, an agent drafts the next communication.
5. Safety and Policy Service reviews it.
6. The platform sends the message or opens a new escalation branch.

## Why Multi-Agent Helps

Multi-agent is justified here because the platform contains distinct reasoning jobs with different failure costs.

Examples:

- intent interpretation must tolerate ambiguous language
- evidence synthesis must stay grounded and cite sources
- motivational coaching must adapt to behavior and tone
- safety review must be conservative and independent

This creates practical benefits:

- different prompts and tools per reasoning job
- independent review of risky responses
- better testability
- lower prompt complexity
- easier future extension

Multi-agent is not justified for:

- CRUD
- scheduling
- policy checks
- fixed calculations
- template filling

## Non-Negotiable Rules

- Frontend clients never call agents directly.
- Agents never write durable state directly.
- Safety runs independently from content generation.
- Health facts require typed persistence, not free-form memory.
- Every user-visible recommendation must be replayable.
