# Product Roadmap

## Purpose
This roadmap aligns the current repository with the target production platform:
- FastAPI backend
- Next.js frontend
- PostgreSQL + Redis production data plane
- LLM-driven orchestration
- RAG-based retrieval
- multi-agent workflow execution

It is explicit about current maturity so contributors can distinguish:
- what is already implemented
- what is being actively hardened
- what remains a research or platform investment

## Current Maturity Snapshot
Current implemented baseline:
- FastAPI + Next.js monorepo with typed API and web contracts
- SQLite-backed auth and application persistence
- action-based authorization and centralized error semantics
- in-process workflow coordination with structured timeline events
- adaptive meal recommendation with online interaction learning
- reminder scheduling and multi-channel delivery with durable logs
- smoke-tested primary web journeys

Current maturity gaps relative to the target platform:
- PostgreSQL is not yet the primary system of record
- Redis is not yet the standard cache / queue / ephemeral state layer
- RAG ingestion, indexing, retrieval, and citation layers are not yet first-class production modules
- agent routing is still partly implemented through service-layer orchestration rather than a dedicated registry/runtime
- offline evaluation, retrieval benchmarking, and research-grade safety evaluation are still early

## Goal Labels
- `Research Goal` — experimental or model-quality work
- `Engineering Goal` — application, workflow, API, and product-delivery work
- `Infrastructure Goal` — runtime, deployment, scale, resilience, and observability work

## Status Labels
- `**[Complete]**` Delivered and validated in the repository
- `**[In Progress]**` Active implementation or immediate hardening target
- `**[Planned]**` Approved backlog item
- `**[Research]**` Requires experimentation before production commitment

## Short-Term (0–3 Months)

### 1. Core Infrastructure
- `**[In Progress]**` PostgreSQL-ready persistence boundary
  - `Engineering Goal`, `Infrastructure Goal`
  - Replace SQLite-specific assumptions in repositories with interfaces that can support PostgreSQL as the production system of record.
  - Exit criteria:
    - application repositories have PostgreSQL-compatible contracts
    - schema groups are documented for auth, health, meals, reminders, and workflow state
    - migration strategy from SQLite fixtures to PostgreSQL-backed environments is defined

- `**[Planned]**` Redis-backed async and ephemeral state layer
  - `Infrastructure Goal`
  - Introduce Redis for cache, distributed locking, short-lived state, and worker coordination.
  - Exit criteria:
    - queue/caching responsibilities are explicitly separated from durable storage
    - reminder and workflow side effects can run through Redis-backed workers without API coupling

- `**[Planned]**` Explicit agent registry and workflow runtime contract
  - `Engineering Goal`
  - Move from service-centric orchestration toward a named registry of agents and durable workflow routing decisions.
  - Exit criteria:
    - agents declare capabilities, allowed tools, and output contracts
    - workflow routing is no longer embedded ad hoc in transport-facing code

- `**[Complete]**` Logging, correlation, and error normalization foundation
  - `Infrastructure Goal`
  - Structured logging, correlation IDs, centralized errors, and workflow timeline capture are already in place.

### 2. AI/ML Components
- `**[In Progress]**` Recommendation-agent hardening and offline refresh hooks
  - `Research Goal`, `Engineering Goal`
  - Extend the current online reranking system with offline refresh and richer diagnostics.
  - Exit criteria:
    - preference snapshot rebuild job exists
    - ranking deltas are explainable after refreshes

- `**[Planned]**` Prompt orchestration standardization
  - `Engineering Goal`
  - Centralize prompt assembly, model selection, and output validation patterns across agents.
  - Exit criteria:
    - prompt construction is no longer scattered across service code
    - agent contracts define prompt inputs and output schemas explicitly

- `**[Research]**` RAG v1 foundation
  - `Research Goal`, `Engineering Goal`
  - Establish ingestion, chunking, embedding, retrieval, and citation packaging boundaries for trusted medical and nutritional sources.
  - Exit criteria:
    - source provenance model defined
    - retrieval service contract defined
    - offline retrieval evaluation set identified

- `**[Planned]**` Safety and guardrail coverage expansion
  - `Research Goal`, `Engineering Goal`
  - Extend safety beyond current recommendation and reminder semantics into retrieval and broader multi-agent outputs.

### 3. Product Features
- `**[Complete]**` User state tracking and personalization baseline
  - `Engineering Goal`
  - Persisted health profiles, household context, meal history, and recommendation interactions are implemented.

- `**[Planned]**` Knowledge retrieval agent
  - `Research Goal`, `Engineering Goal`
  - Add a first-class knowledge retrieval path that can support evidence-backed user guidance.

- `**[Research]**` Emotional support and escalation agent
  - `Research Goal`
  - Explore bounded emotional-state classification, safe language generation, and escalation rules.

- `**[Complete]**` Reminder automation and multi-channel scheduling baseline
  - `Engineering Goal`
  - Durable preferences, endpoints, schedules, logs, and reminder delivery adapters are implemented.

### 4. Deployment and Scaling
- `**[Complete]**` API container baseline
  - `Infrastructure Goal`
  - A production-style Dockerfile and CI validation pipeline already exist.

- `**[Planned]**` Environment profiles and secret hygiene
  - `Infrastructure Goal`
  - Introduce explicit development, staging, and production configuration profiles.

- `**[Planned]**` Readiness and dependency diagnostics
  - `Infrastructure Goal`
  - Expose richer runtime readiness for providers, workers, and persistence layers.

## Mid-Term (3–9 Months)

### 1. Core Infrastructure
- `**[Planned]**` Multi-process worker topology
  - `Infrastructure Goal`
  - Introduce dedicated worker processes for notifications, retrieval ingestion, offline learning refresh, and heavy orchestration tasks.

- `**[Planned]**` Event bus and workflow durability improvements
  - `Engineering Goal`, `Infrastructure Goal`
  - Move from in-process workflow sequencing toward durable workflow state transitions and replayable event streams.

- `**[Planned]**` Agent capability routing
  - `Engineering Goal`
  - Add a capability-driven router so workflows can resolve the correct agent set by task rather than by direct service composition.

### 2. AI/ML Components
- `**[Planned]**` RAG productionization
  - `Research Goal`, `Engineering Goal`
  - Complete retrieval indexing, ranking, citation rendering, and source trust controls.

- `**[Planned]**` Memory hierarchy
  - `Research Goal`, `Engineering Goal`
  - Separate short-term session memory, durable user memory, and retrieval-backed knowledge memory.

- `**[Research]**` Evaluation framework and prompt regression platform
  - `Research Goal`, `Infrastructure Goal`
  - Add offline datasets, prompt snapshots, task metrics, and benchmark dashboards.

### 3. Product Features
- `**[Planned]**` Chronic condition monitoring workflows
  - `Engineering Goal`, `Research Goal`
  - Add condition-aware alerting, longitudinal trend views, and policy-controlled recommendations.

- `**[Planned]**` Knowledge-grounded assistant experiences
  - `Engineering Goal`
  - Surface retrieval-backed answers and explanation cards in the web product.

- `**[Planned]**` Personalization maturity phase 2
  - `Engineering Goal`, `Research Goal`
  - Improve adherence-aware coaching, meal substitution quality, and habit-loop modeling.

### 4. Deployment and Scaling
- `**[Planned]**` Horizontal scale readiness
  - `Infrastructure Goal`
  - Add Redis-backed coordination, stateless API assumptions, and load-balancer-safe session behavior.

- `**[Planned]**` Monitoring stack expansion
  - `Infrastructure Goal`
  - Add metrics, tracing, alerting thresholds, and operator dashboards for workflow and provider health.

- `**[Planned]**` Cache strategy formalization
  - `Infrastructure Goal`
  - Define cache boundaries for retrieval, session-adjacent state, and read-heavy product surfaces.

## Long-Term (9–18 Months)

### 1. Core Infrastructure
- `**[Planned]**` Full production data plane on PostgreSQL + Redis
  - `Infrastructure Goal`
  - Retire SQLite from primary production responsibility and make PostgreSQL + Redis the supported runtime standard.

- `**[Planned]**` Durable multi-agent execution engine
  - `Engineering Goal`, `Infrastructure Goal`
  - Support resilient long-running workflows, replay, compensation, and multi-agent concurrency.

### 2. AI/ML Components
- `**[Research]**` Agent ensemble optimization
  - `Research Goal`
  - Experiment with routing strategies, model specialization, and confidence-aware fallback chains.

- `**[Research]**` Human-in-the-loop evaluation and safety review tooling
  - `Research Goal`, `Infrastructure Goal`
  - Add review queues, adjudication surfaces, and dataset capture for agent behavior quality.

- `**[Planned]**` Retrieval-aware safety and evidence scoring
  - `Research Goal`, `Engineering Goal`
  - Make citation quality and source trust first-class factors in agent outputs.

### 3. Product Features
- `**[Planned]**` Cross-channel conversational product surface
  - `Engineering Goal`
  - Support coherent user journeys across web, Telegram, WhatsApp, and WeChat with shared memory and workflow state.

- `**[Research]**` Emotional support escalation framework
  - `Research Goal`
  - Introduce clinically safe escalation patterns, crisis boundaries, and operator controls where product policy allows.

- `**[Planned]**` Advanced personalization and chronic-care programs
  - `Engineering Goal`, `Research Goal`
  - Move from isolated recommendations toward longitudinal coaching programs and condition-specific workflows.

### 4. Deployment and Scaling
- `**[Planned]**` Fault-tolerant multi-region or multi-zone runtime posture
  - `Infrastructure Goal`
  - Add stronger recovery guarantees for queues, workers, and durable event processing.

- `**[Planned]**` Policy-driven feature rollout and experimentation
  - `Infrastructure Goal`, `Engineering Goal`
  - Add environment-aware feature flags and controlled rollout paths for new agents and tools.

- `**[Planned]**` Advanced configuration telemetry and auditability
  - `Infrastructure Goal`
  - Make runtime configuration provenance and effective values observable with redaction by default.
