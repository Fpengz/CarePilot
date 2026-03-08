# Architecture

## Purpose
This document is the canonical architecture reference for Dietary Guardian.

It serves two audiences:
- engineers onboarding to the current codebase
- future contributors extending the system toward a production multi-agent architecture built on FastAPI, Next.js, PostgreSQL, Redis, RAG, and specialized workflow-driven agents

Companion documentation:
- `docs/README.md`
- `docs/system-overview.md`
- `docs/codebase-walkthrough.md`
- `docs/developer-guide.md`
- `docs/user-manual.md`
- `docs/operations-runbook.md`

This document is explicit about the difference between:
- the current repository baseline
- the target production architecture

## Current Maturity Snapshot
The repository is currently a strong v1 baseline with these production-relevant capabilities already implemented:
- FastAPI API with centralized error handling, request context middleware, and action-based authorization
- Next.js web client with typed API bindings and validated user flows
- shared Python core under `src/dietary_guardian`
- workflow coordination for meal analysis and alert/reminder delivery
- adaptive meal recommendation with persisted profile state and online interaction learning
- durable reminder notification scheduling, logs, and multi-channel delivery adapters
- SQLite-backed persistence by default
- a DB-backed outbox worker pattern for asynchronous delivery

The repository does not yet fully implement the target platform in these areas:
- PostgreSQL as the primary system of record
- Redis as the standard cache / queue / ephemeral state layer
- a full RAG retrieval and indexing pipeline
- a dedicated multi-agent worker runtime with external message bus semantics
- specialized emotional-support and knowledge-retrieval agents as first-class production services

The architecture below therefore describes both:
- the current operating model
- the intended production landing zone

## High-Level System Overview
Dietary Guardian should be understood as a layered system.

### 1. Interface Layer
Responsibilities:
- render user-facing experiences
- collect structured inputs
- present recommendation, reminder, and workflow state
- expose messaging entry points such as web, mobile web, Telegram, WhatsApp, or WeChat integrations

Current implementation:
- Next.js app under `apps/web`
- Streamlit demo/internal surface under `src/app.py`

Target production expansion:
- web client remains primary surface
- messaging adapters become first-class external interfaces
- future mobile/native clients should integrate through the same API and event contracts

### 2. API Layer
Responsibilities:
- authenticate and authorize requests
- validate transport payloads
- map HTTP concerns to application services
- normalize errors and trace metadata

Current implementation:
- FastAPI app under `apps/api/dietary_api`
- route modules remain intentionally thin

### 3. Orchestration Layer
Responsibilities:
- coordinate multi-step workflows
- decide which agent or service executes next
- propagate request IDs, correlation IDs, and workflow events
- separate business orchestration from HTTP and UI concerns

Current implementation:
- `src/dietary_guardian/services/workflow_coordinator.py`
- API services under `apps/api/dietary_api/services/*`
- recommendation orchestration in shared services

Target production expansion:
- explicit workflow engine with durable state transitions
- event-driven handoff between agents
- worker boundary for asynchronous or long-running orchestration

### 4. Agent Layer
Responsibilities:
- perform specialized reasoning or decision support
- build prompts and context windows
- invoke tools when required
- validate outputs before persistence or delivery

Current implementation:
- meal analysis and recommendation-oriented agent logic exists in `src/dietary_guardian/agents` and `src/dietary_guardian/services/recommendation_agent_service.py`

Target production agent set:
- Diet Analysis Agent
- Knowledge Retrieval Agent
- Emotional Support Agent
- Reminder Engine
- Safety / Guardrail Agent
- Coordinator / Router Agent

### 5. Tool Layer
Responsibilities:
- expose side-effectful capabilities through typed contracts
- enforce policy and environment restrictions
- support safe external integrations

Current implementation:
- tool registry under `src/dietary_guardian/services/tool_registry.py`
- platform tool bindings in `src/dietary_guardian/services/platform_tools.py`

### 6. Data Layer
Responsibilities:
- store durable domain state
- store workflow and audit events
- support retrieval, memory, and recommendation state
- provide cache and queue primitives

Current implementation:
- SQLite repositories for app data and auth
- in-memory memory services for some workflow state
- outbox table for async delivery

Target production expansion:
- PostgreSQL for durable relational state
- Redis for ephemeral state, cache, distributed locking, and queue coordination
- vector index / embedding store for RAG

## Request Lifecycle
A typical production request lifecycle should be understood as follows:

1. A user sends input from the web client or a messaging channel.
2. The Interface Layer forwards the request to the FastAPI API.
3. The API Layer authenticates the caller, checks scopes/policies, validates the payload, and attaches request/correlation IDs.
4. The API Layer delegates to an application or orchestration service.
5. The Orchestration Layer resolves the active workflow and gathers required state:
   - user profile
   - household context
   - health profile
   - meal history
   - reminder state
   - retrieval context if RAG is enabled
6. The Orchestration Layer invokes one or more specialized agents.
7. Agents may call registered tools through the Tool Layer.
8. Outputs are validated, safety-checked, and normalized.
9. The system persists domain changes and workflow events.
10. If side effects are required, they are enqueued through the async delivery path instead of running in the request thread.
11. The API returns a typed response to the frontend.
12. Background workers continue asynchronous tasks such as notifications, indexing, or model refresh jobs.

## System Diagram Explained in Words
The architecture diagram can be described as the following flow:

- The user interacts with the system through the Next.js web app or external messaging channels.
- All inbound traffic terminates at the FastAPI API layer.
- The API forwards requests to orchestration services that determine which workflow applies.
- The workflow coordinator resolves context and invokes specialized agents.
- Agents do not directly call infrastructure or external services. They call tools through a registry and policy layer.
- The RAG subsystem sits beside the agent layer:
  - retrieval requests go to a retrieval service
  - retrieval service queries indexed knowledge sources and vector search
  - retrieved context is returned to prompt assembly before agent execution
- Durable state such as users, sessions, households, reminders, recommendation history, and audit records belongs in PostgreSQL in the target architecture.
- Ephemeral state such as cache entries, queue signals, locks, and short-lived conversation buffers belongs in Redis in the target architecture.
- Worker processes consume queued jobs for notification delivery, indexing, offline evaluation, and model-refresh tasks.
- Observability spans every layer through structured logs, request IDs, correlation IDs, metrics, and workflow event timelines.

## Codebase Structure Walkthrough
The current repository structure is a monorepo and should be interpreted as follows.

```text
apps/
  api/
    dietary_api/
      main.py
      deps.py
      middleware.py
      policy.py
      routers/
      services/
  web/
    app/
    components/
    lib/
    e2e/
src/
  dietary_guardian/
    agents/
    application/
    config/
    infrastructure/
    models/
    observability/
    safety/
    services/
docs/
scripts/
tests/
```

Repository note:
- `src/dietary_guardian/domain/` is intentionally omitted in the current baseline. Domain rules currently live in `models/` and `services/` until aggregate boundaries are introduced explicitly.

### `apps/api/`
FastAPI transport application.

Important files:
- `apps/api/dietary_api/main.py` — FastAPI app factory and middleware wiring
- `apps/api/dietary_api/deps.py` — app context construction and dependency container
- `apps/api/dietary_api/routers/` — HTTP routes only
- `apps/api/dietary_api/services/` — API-facing orchestration and DTO shaping

### `apps/web/`
Next.js frontend.

Important directories:
- `apps/web/app/` — route segments and page entry points
- `apps/web/components/` — reusable UI building blocks
- `apps/web/lib/api/` — domain-scoped typed API clients
- `apps/web/lib/types.ts` — client-side response and domain view types
- `apps/web/e2e/` — browser smoke coverage

### `src/dietary_guardian/agents/`
Agent- and provider-specific logic.

Current examples:
- LLM provider factory
- meal vision agent logic
- dietary reasoning agent logic

### `src/dietary_guardian/application/`
Target home for use cases, policies, and ports.

Current usage:
- auth use cases
- household use cases
- suggestions use cases
- policy boundaries

### `src/dietary_guardian/infrastructure/`
Infrastructure adapters.

Current usage:
- auth persistence/signing
- household storage

Target expansion:
- PostgreSQL repositories
- Redis cache/queue adapters
- vector store adapters
- external messaging clients

### `src/dietary_guardian/models/`
Typed contracts and data models.

Current usage:
- reminder, recommendation, health-profile, workflow, alerting, and output models

### `src/dietary_guardian/services/`
Business orchestration and domain-level service logic.

Current usage:
- repository implementation
- workflow coordinator
- recommendation engine
- reminder notification scheduler
- alerting/outbox worker
- memory services

Target direction:
- keep service orchestration cohesive, move transport concerns to `apps/api`, and keep persistence adapters in `infrastructure/`

### `docs/`
Architecture notes, API contracts, roadmap, runbooks, and operations documentation.
Use `docs/README.md` as the index for the active modular documentation suite.

### `scripts/`
Developer-entry scripts and operational helpers.

### `tests/`
Repository-level unit and integration tests.

## Backend Entry Points
### FastAPI App Initialization
Primary entry point:
- `apps/api/dietary_api/main.py`

Responsibilities:
- construct or attach `AppContext`
- register middleware
- register routers
- install centralized exception handlers
- manage startup/shutdown lifecycle

### App Context Initialization
Primary entry point:
- `apps/api/dietary_api/deps.py`

Responsibilities:
- load settings
- initialize repositories and auth stores
- initialize workflow coordinator
- initialize tool registry
- initialize memory/timeline services

### Route Registration
Primary entry point:
- `apps/api/dietary_api/routers/__init__.py`

Responsibilities:
- compose all API route modules into a single app

### Agent Registry / Provider Initialization
Current provider/runtime setup:
- `src/dietary_guardian/agents/provider_factory.py`

Target extension:
- introduce an explicit `AgentRegistry` that resolves named agents by capability rather than direct imports

### Workflow Coordinator
Primary current entry point:
- `src/dietary_guardian/services/workflow_coordinator.py`

Responsibilities:
- define workflow sequences
- append timeline events
- hand off between logical agents
- coordinate tool invocation through the tool registry

### Tool Binding System
Primary entry points:
- `src/dietary_guardian/services/tool_registry.py`
- `src/dietary_guardian/services/platform_tools.py`

Responsibilities:
- register tools with schemas and policy constraints
- validate input/output contracts
- capture tool metrics and failures

## Frontend Entry Points
### Next.js Root Layout
Primary entry point:
- `apps/web/app/layout.tsx`

Responsibilities:
- load global CSS
- install app shell
- install session provider
- define top-level metadata and accessibility scaffolding

### Root Navigation Entry Point
Primary entry point:
- `apps/web/app/page.tsx`

Responsibilities:
- redirect authenticated users to the dashboard
- redirect unauthenticated users to login

### API Integration Layer
Primary entry point:
- `apps/web/lib/api.ts`

Responsibilities:
- same-origin API requests through `/backend`
- cookie-aware fetch behavior
- typed response parsing
- frontend dev logging hooks

### State Management
Current pattern:
- route-local React state plus shared session provider
- typed state hydration from API responses

Target production direction:
- keep server/client boundaries explicit
- only promote shared global state when needed for session, realtime presence, or optimistic workflow updates

### Chat / Session Persistence
Current implementation:
- auth session and app state persist through backend cookies and database storage

Target direction:
- if chat-first or messaging-first surfaces are introduced, conversation thread state should persist in PostgreSQL while transient typing/presence state stays in Redis

## Database and State Flow
## Current Repository Default
Current durable storage:
- SQLite app database for reminders, meals, suggestions, recommendation state, and outbox records
- SQLite auth database for users, sessions, and audit events

Current transient state:
- in-memory profile memory
- in-memory clinical snapshot memory
- in-memory workflow timeline accumulation inside app process

This is acceptable for local-first v1, but it is not the final production target.

## Target Production State Topology
### PostgreSQL
PostgreSQL should become the system of record for:
- users
- auth sessions and audit events
- households and membership
- meal records
- health profiles
- biomarker readings
- reminders and notification schedules
- recommendation artifacts and interaction events
- workflow executions and agent logs
- knowledge-source metadata

Recommended high-level schema groups:
- `identity`: users, sessions, audit events
- `health`: profiles, biomarkers, chronic-condition records
- `meals`: meal captures, nutrition summaries, recommendation artifacts
- `messaging`: reminders, notification preferences, delivery logs
- `workflow`: executions, handoffs, tool invocations, agent traces
- `knowledge`: source metadata, ingestion jobs, chunk/index metadata

### Redis
Redis should be used for:
- request-scoped ephemeral coordination when workflow fan-out grows
- caching hot reads
- distributed locks
- rate limiting
- Celery or worker queue coordination
- short-lived conversation context and response streaming coordination

### Memory Strategy
Use three distinct memory classes:
- short-term memory: Redis / request-local ephemeral context
- user memory: PostgreSQL-backed durable summaries and preference state
- knowledge memory: RAG document store + vector index

### Event-Driven State Updates
Preferred production pattern:
- APIs write durable state first
- side effects are emitted to an outbox or queue
- workers process asynchronous delivery, indexing, evaluation, and refresh jobs
- workflow and agent events are appended as immutable logs

## Agent Lifecycle
A production agent lifecycle should follow the same strict pattern regardless of agent type.

1. Resolve agent identity and workflow role.
2. Load policy context and safety context.
3. Assemble prompt or structured reasoning input from:
   - user state
   - workflow state
   - memory state
   - RAG retrieval context if applicable
4. Decide whether tool usage is required.
5. Invoke tools only through the registry or tool binding layer.
6. Validate the output against a typed contract.
7. Apply safety and post-generation validation.
8. Persist workflow events, selected outputs, and evaluation metadata.
9. Update durable memory if the result should influence future behavior.
10. Emit metrics and structured logs.

### Agent Registration
Recommended target contract:
- each agent has a stable name
- each agent declares supported tasks
- each agent declares allowed tools
- each agent declares output schema

### Prompt Assembly
Prompt assembly should be centralized per agent family.
Do not scatter prompt strings in route handlers or UI code.

### Tool Call Decision
Agents should not directly import infrastructure clients.
They should emit tool requests against registered tool interfaces.

### Response Validation
Every agent output should be:
- schema-validated
- safety-checked
- logged with correlation metadata

### Memory Updates
Only persist memory when the signal is stable and useful.
Examples:
- accepted substitutions
- repeated meal preferences
- reminder channel preferences
- high-confidence chronic-condition-related guidance outcomes

Do not persist raw speculative emotional or medical conclusions without explicit product intent and retention rules.

## RAG Integration Model
RAG is not yet a first-class implemented subsystem in this repository, but the architecture should treat it as a dedicated service boundary.

Recommended production components:
- document ingestion pipeline
- chunking and metadata enrichment
- embedding generation
- vector index adapter
- retrieval ranking service
- citation packaging service

Recommended flow:
1. ingest trusted medical or nutritional sources
2. normalize and chunk documents
3. generate embeddings
4. store chunk metadata and vectors
5. retrieve by intent and user context
6. pass only filtered, cited evidence into prompt assembly
7. log retrieved sources for auditability

## Extension Guidelines
## Adding a New Agent
1. Define the agent's responsibility and boundaries.
2. Add a typed input/output contract.
3. Implement prompt assembly and validation in a dedicated module.
4. Register the agent in the workflow routing layer or future registry.
5. Explicitly declare which tools the agent may call.
6. Add workflow, API, and evaluation coverage.

Guardrails:
- no direct database access from agent code
- no direct HTTP calls to external tools from agent code
- no untyped outputs crossing workflow boundaries

## Adding a New Tool
1. Define input and output schemas.
2. Define required scopes and allowed environments.
3. Register the tool through the tool registry.
4. Implement infrastructure side effects in adapters, not in policy or router code.
5. Add validation, failure-path tests, and observability hooks.

Guardrails:
- tools must be policy-aware
- tools must return structured errors
- tools must be idempotent where possible

## Adding a New Data Source
1. Define trust level and data ownership.
2. Define ingestion contract and update cadence.
3. Add adapter module and normalization rules.
4. Add storage/indexing path.
5. Add provenance metadata.
6. Add security review for secrets, PII, and licensing.

## Modifying Workflow Routing
1. Change routing logic in orchestration modules, not route handlers.
2. Add explicit entry and exit criteria for each step.
3. Preserve correlation/request propagation.
4. Add replay-safe logging and tests.

## Extending the RAG Pipeline
1. Add source adapter
2. add chunker/normalizer
3. add embedding job
4. add retrieval evaluation set
5. add citation rendering and audit capture

Do not allow arbitrary retrieval content to bypass the safety layer.

## Testing and Evaluation
### Unit Tests
Required for:
- domain rules
- tool contracts
- routing decisions
- scheduler and retry behavior
- repository state transitions

### Integration Tests
Required for:
- API contracts
- workflow execution paths
- notification delivery scheduling
- agent orchestration boundaries
- auth and policy checks

### Prompt Regression Testing
Required for agentic features that rely on prompt assembly.

Recommended approach:
- stable fixture inputs
- snapshot or contract assertions on normalized outputs
- explicit review when prompt templates change

### Offline Evaluation
Required as RAG and multi-agent reasoning mature.

Recommended evaluation categories:
- retrieval quality
- recommendation acceptance/adherence
- safety false-negative rate
- emotional-support escalation correctness
- reminder delivery success rate

### Observability Metrics
Minimum recommended metrics:
- request count and latency by route
- workflow duration by workflow name
- tool success/failure rate
- notification delivery success/retry/dead-letter rates
- recommendation interaction rates
- retrieval hit rate and citation coverage
- safety refusal / escalation rates

## Architectural Principles
The following principles are mandatory for future extension:
- thin transport layers
- typed boundaries
- policy-first side effects
- durable event capture for workflows
- explicit separation between orchestration, agent logic, and infrastructure
- safe fallback behavior when LLM or external providers fail
- no hidden cross-layer shortcuts
