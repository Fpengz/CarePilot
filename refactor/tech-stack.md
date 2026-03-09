# Tech Stack

## Purpose

Define the recommended implementation stack for the refactor package, with explicit guidance for:

- hackathon delivery now
- scalable evolution later
- where to avoid unnecessary complexity

## Decision Framework

This stack is optimized for:

- shipping quickly
- keeping the architecture coherent
- preserving a path to production-grade evolution

It is not optimized for:

- maximum theoretical purity
- early microservice decomposition
- collecting every fashionable AI framework

## Recommended Stack Summary

### Hackathon Now

- `Frontend`: Next.js App Router, TypeScript, TanStack Query
- `API`: FastAPI, Pydantic v2
- `Persistence`: SQLite by default, with optional PostgreSQL only if the team needs shared target-aligned infra during the hackathon
- `Vector search`: Chroma behind an internal `EvidenceRetrievalPort`
- `Cache and ephemeral state`: Redis
- `Background jobs`: Celery
- `Agent runtime`: PydanticAI
- `Orchestration`: explicit Python Care Orchestrator
- `Perception`: Gemini Flash or equivalent fast multimodal model
- `Report parsing`: MarkItDown
- `Testing`: pytest, Playwright
- `Safety simulation`: Hypothesis
- `Observability`: Logfire or OpenTelemetry baseline

### Scale Later

- `Workflow durability`: Temporal
- `Advanced agent graph orchestration`: LangGraph if needed
- `Retrieval backend`: evaluate pgvector if tighter joins or simpler platform governance are needed
- `Search expansion`: hybrid lexical + vector retrieval with richer reranking
- `Infra`: split runtimes by gateway, orchestrator, workflows, and agents

## Frontend

### Recommended

- `Next.js`
- `TypeScript`
- `TanStack Query`

Why:

- current repo already uses Next.js
- typed client state is useful for workflow-driven UI
- TanStack Query handles cache, background refetch, optimistic updates, and mutation states cleanly

Good fit for:

- chat and form hybrids
- workflow task UIs
- reminders and timeline views
- caregiver and household dashboards

## Backend API

### Recommended

- `FastAPI`
- `Pydantic v2`

Why:

- current repo already aligns with this
- good typed contract ergonomics
- easy boundary between transport and orchestration
- easy schema reuse for agent input and output contracts

Good fit for:

- synchronous interaction APIs
- observation ingestion
- workflow action endpoints
- internal service boundary models

## Persistence

### Recommended

- `SQLite` for the default hackathon posture
- optional `PostgreSQL` when the team explicitly wants target-aligned shared infra

Why:

- aligns with the current repo's local-first posture
- reduces infra overhead during the hackathon
- preserves a simple path for demos and rapid iteration

Why PostgreSQL may still be used:

- shared team development environment
- target-aligned infra demos
- stronger multi-user operational realism

Avoid for hackathon:

- splitting core state across multiple databases too early

## RAG and Retrieval

### Recommendation

- `Chroma` now, wrapped behind an internal `EvidenceRetrievalPort`

Why this is the active hackathon choice:

- the teammate-owned data is already embedded in Chroma
- re-embedding or migrating retrieval now would waste hackathon time
- the adapter keeps the rest of the platform independent from the storage choice

Good fit for:

- curated evidence packs
- guideline retrieval
- educational content lookup
- condition-specific retrieval
- citation packaging

### Why Chroma Works For This Hackathon

Use Chroma here because the goal is:

- immediate reuse of an existing index
- fast retrieval prototyping
- low migration cost during the hackathon

### Long-Term Architectural Preference

For a greenfield long-term governed platform, `PostgreSQL + pgvector` is still attractive because:

- retrieval here is not generic question-answering over arbitrary files
- the system needs versioned medical content, policy tags, condition metadata, and auditability
- keeping embeddings and metadata close to the operational store reduces architecture friction

### Long-Term Retrieval Direction

Evolve toward:

- hybrid lexical + vector retrieval
- curated knowledge packs
- content versioning
- audience and reading-level metadata
- reranking layer for evidence prioritization
- optional migration from Chroma to pgvector if the adapter boundary is no longer enough

## Cache and Ephemeral State

### Recommended

- `Redis`

Use it for:

- queue broker
- idempotency keys
- short-lived conversation summaries
- workflow timers or coordination
- rate limits
- locks

Do not use Redis as the primary durable store for user health state.

## Background Jobs

### Hackathon Recommendation

- `Celery`

Why:

- mature and widely understood
- good for indexing, reminders, scheduled nudges, notification delivery, async processing, and batch work
- sufficient for hackathon-scale background execution

Good fit for:

- sending reminders
- embedding documents
- rebuilding retrieval indexes
- nightly evaluations
- delayed follow-up messages

### What Celery Is Not Great At

- highly durable, long-running, multi-step workflows over days or weeks
- complex human-in-the-loop orchestration
- replay-driven workflow semantics

### Scale-Later Recommendation

- `Temporal`

Use Temporal when you need:

- durable workflow execution
- timers over long periods
- exact resume semantics
- replayable workflow state
- complex care programs with pauses, escalations, and branching

Good fit for:

- symptom follow-up sequences
- care escalation timers
- weekly and monthly health programs
- caregiver workflows
- multi-step adherence recovery journeys

### Practical Recommendation

- use `Celery` now
- use it only for bounded workflows with short timers and explicit persisted state transitions
- promote `Temporal` before shipping multi-day or human-in-the-loop care programs that require exact resume and replay semantics

## Agent Runtime

### Recommended

- `PydanticAI`

Why:

- strong typed output model
- good fit with Pydantic contracts
- supports tools, multi-agent patterns, evals, and graph-like composition
- aligns with the current Python stack

Good fit for:

- IntentContextAgent
- CarePlanningAgent
- EvidenceSynthesisAgent
- MotivationalSupportAgent
- SafetyReviewAgent

Not the primary place for:

- meal image perception
- OCR or report extraction
- deterministic local-food substitution rules

Guideline:

- keep agent count low
- require typed outputs
- use agents only for non-deterministic reasoning

## Orchestration

### Hackathon Recommendation

- explicit Python `Care Orchestrator`

Why:

- easiest to control
- easiest to debug
- keeps architecture visible
- avoids overcommitting to a framework before the flows stabilize

This orchestrator should:

- load case state
- call deterministic capabilities
- call agents selectively
- invoke safety review
- commit events and next actions

## What LangGraph Can Help With

LangGraph is useful when agent orchestration becomes explicitly graph-shaped and stateful.

It helps with:

- node-based execution graphs
- branching logic
- checkpointing
- resume after interruption
- human-in-the-loop pauses
- durable multi-step agent flows

Good fit if your interaction flow looks like:

- classify intent
- ask follow-up questions
- wait for user answer
- continue from prior state
- invoke safety review
- either answer or escalate

### Why Not Default to LangGraph for the Hackathon

- it introduces another orchestration abstraction
- it is easy to over-engineer early flows
- explicit Python orchestration is simpler until the flow complexity proves the need

### Recommendation

- start with explicit Python orchestration
- adopt `LangGraph` only if the team wants graph-native agent flows with resumability and already understands the framework well

## Safety Layer

### Recommended

- deterministic policy service implemented in Python
- optional model-assisted safety review through a dedicated agent

Do not use a framework as a substitute for:

- policy definitions
- escalation rules
- medical safety logic

The safety system should be mostly framework-agnostic.

## Testing and Validation

### Recommended

- `pytest`
- `Playwright`

Use pytest for:

- contract tests
- policy tests
- orchestrator tests
- agent output schema tests

Use Playwright for:

- end-to-end user workflows
- chat and form behavior
- escalation UI states
- reminder and follow-up UX validation

## Observability

### Recommended

- `Logfire` for fast developer visibility
- `OpenTelemetry` concepts for long-term tracing structure

Track:

- request IDs
- workflow IDs
- agent runs
- policy decisions
- evidence IDs
- latency and failure rates

## What To Avoid

Avoid introducing all of the following at once:

- Chroma plus pgvector
- Celery plus Temporal plus another queue
- LangGraph plus a second agent orchestration framework plus custom graph logic
- too many specialist agents
- microservices split before the boundaries are exercised

Pick one default in each area and keep the platform legible.

## Final Recommendations

### Best Hackathon Stack

- `Next.js`
- `TanStack Query`
- `FastAPI`
- `Pydantic`
- `PostgreSQL`
- `Chroma` behind `EvidenceRetrievalPort`
- `Redis`
- `Celery`
- `PydanticAI`
- explicit Python `Care Orchestrator`
- `pytest`
- `Playwright`

### Best Evolution Path

- keep the retrieval layer behind `EvidenceRetrievalPort`
- evaluate `pgvector` later if tighter metadata joins or simpler platform governance become more important than reuse of the existing Chroma index
- keep `Celery` for jobs
- introduce `Temporal` only for durable care workflows
- introduce `LangGraph` only if agent flows become deeply graph-shaped and resumable

This keeps the system fast to build now without painting the architecture into a corner.
