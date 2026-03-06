# Contributing

## Purpose
This document defines how contributors should work in the Dietary Guardian repository.

It is written for:
- backend engineers
- frontend engineers
- ML / applied AI engineers
- platform engineers
- future AI agents operating on the repository

The project favors maintainability over cleverness. New contributions should make the architecture easier to extend, not merely add behavior.

## Repository Operating Model
The repository is a monorepo with:
- FastAPI backend under `apps/api`
- Next.js frontend under `apps/web`
- shared Python core under `src/dietary_guardian`
- tests at both API and repository levels

Current local-first default:
- SQLite for durable storage
- in-process orchestration for most workflows

Target production direction:
- PostgreSQL for primary durable state
- Redis for cache, ephemeral coordination, and async worker plumbing
- expanded worker and retrieval infrastructure

Contributors must preserve compatibility with the current implementation while moving the codebase toward the target architecture.

## Getting Started
### Requirements
Required:
- Python 3.12+
- Node.js 20+
- `uv`
- `pnpm`

Recommended:
- Docker for container validation
- Playwright browser dependencies for web e2e

### Install Dependencies
```bash
uv sync
pnpm install
```

### Environment Setup
Create local environment configuration:

```bash
cp .env.example .env
```

Configuration rules:
- root `.env` is the default source of truth
- optional `apps/web/.env` may override root values for web commands only
- never commit `.env`

### Local Development
Run the full local stack:

```bash
uv run python scripts/dg.py dev
```

Useful variants:

```bash
uv run python scripts/dg.py dev --no-web
uv run python scripts/dg.py dev --no-api
pnpm dev:scheduler
```

Endpoints:
- web: `http://localhost:3000`
- API docs: `http://localhost:8001/docs`

### Docker
The repository currently includes a production-style API container via the root `Dockerfile`.

Build:

```bash
docker build -t dietary-guardian .
```

Run:

```bash
docker run --rm -p 8001:8001 --env-file .env dietary-guardian
```

Current limitation:
- the repository does not yet include a full `docker-compose` or equivalent local stack for PostgreSQL + Redis
- introducing that stack is a valid roadmap contribution, not an existing assumption

## Development Workflow
### Branch Strategy
Use short-lived feature branches from `main`.

Recommended naming:
- `feat/<topic>`
- `fix/<topic>`
- `docs/<topic>`
- `refactor/<topic>`

### Pull Request Guidelines
Each PR should:
- focus on one coherent change set
- include tests or an explicit testing explanation
- describe behavior changes and migration risks
- identify affected layers: API, orchestration, agent, tool, data, frontend, infra

PRs that mix unrelated refactors with feature work should be split.

### Commit Message Standard
Use Conventional Commits.

Format:
- `<type>(<scope>): <subject>`

Examples:
- `feat(reminders): add scheduled notification delivery architecture`
- `fix(auth): reject corrupted sqlite session payloads`
- `docs(architecture): define target multi-agent runtime boundaries`

### Code Review Expectations
Reviewers should focus on:
- correctness
- boundary hygiene
- regression risk
- safety implications
- test coverage
- observability impact

A contribution is not complete if it only works locally but is opaque to operate or debug.

## Coding Standards
## Python Standards
- Follow PEP 8 and repository lint settings.
- Type hints are required for new code.
- Prefer `pydantic` models for structured payloads crossing subsystem boundaries.
- Keep route handlers thin.
- Keep infrastructure logic out of agent logic.

### Async Usage Rules
- Use async where the framework or IO boundary benefits from it.
- Do not introduce async only for style.
- Avoid mixing sync and async flows without a clear boundary.
- Background or retriable side effects should move to worker or outbox paths rather than blocking request handlers.

### Logging Standards
- Use structured logs with request ID and correlation ID when available.
- Log state transitions and failures, not only final outcomes.
- Redact secrets and sensitive personal data.
- Never log raw credentials, tokens, or unbounded user-sensitive payloads.

### Error Handling Patterns
- Use centralized API error helpers for transport-layer failures.
- Return typed, machine-readable error codes.
- Preserve backward-compatible response semantics unless explicitly changing the contract.
- Use retry-safe patterns for side effects.

## Frontend Standards
- Use typed API clients from `apps/web/lib/api.ts`.
- Add new response types to `apps/web/lib/types.ts`.
- Prefer explicit UX states: loading, empty, error, success, partial.
- Keep view logic separate from raw API payload formatting where possible.
- Maintain mobile usability and keyboard accessibility.

Small example:

```ts
export type DailyInsight = {
  id: string;
  title: string;
  summary: string;
};

export async function getDailyInsights(): Promise<DailyInsight[]> {
  return request<DailyInsight[]>("/api/v1/insights/daily");
}
```

## Architecture Rules for Contributors
Mandatory rules:
- routers are HTTP mapping only
- orchestration belongs in services/use cases
- tools are invoked through typed registries
- side effects should be decoupled from request-time business logic
- persistent state transitions must be observable and testable
- new AI behaviors must preserve safety boundaries

Small example:

```python
@router.get("/insights/daily", response_model=list[DailyInsightResponse])
def list_daily_insights(
    user: AuthenticatedUser = Depends(require_user),
    service: InsightService = Depends(get_insight_service),
) -> list[DailyInsightResponse]:
    return [DailyInsightResponse.model_validate(item) for item in service.list_for_user(user.user_id)]
```

The router maps HTTP only. Ranking, retrieval, or other orchestration belongs in `InsightService`.

## How to Add a New Agent
1. Define the agent's responsibility.
   - Example: knowledge retrieval, emotional support, reminder planning.
2. Define typed input and output contracts.
3. Add or extend prompt assembly in a dedicated module.
4. Register the agent in the orchestration layer or future agent registry.
5. Define allowed tools and policy constraints.
6. Add tests for:
   - successful execution
   - failure path
   - safety escalation or refusal path
   - output schema validation
7. Add observability:
   - workflow event logging
   - latency and failure metrics

Checklist:
- no direct route-handler business logic
- no direct untyped external API calls from the agent
- no raw prompt strings hidden in unrelated modules

Small example:

```python
from pydantic import BaseModel


class KnowledgeAgentInput(BaseModel):
    question: str
    user_id: str


class KnowledgeAgentOutput(BaseModel):
    answer: str
    citations: list[str]


class KnowledgeRetrievalAgent:
    def __init__(self, retrieval_service: RetrievalService) -> None:
        self._retrieval_service = retrieval_service

    def run(self, payload: KnowledgeAgentInput) -> KnowledgeAgentOutput:
        context = self._retrieval_service.search(payload.question)
        return KnowledgeAgentOutput(
            answer=f"Grounded answer for: {payload.question}",
            citations=[item.source_id for item in context],
        )
```

Registration should happen in orchestration or registry code, not inside route handlers.

## How to Add a Tool
1. Define the tool input schema.
2. Define the tool output schema.
3. Define required scopes and allowed environments.
4. Register the tool in the tool registry.
5. Implement adapter logic in the infrastructure or service layer.
6. Add integration tests for policy, success, and failure semantics.

A tool must:
- validate input and output
- return structured errors
- be observable
- respect idempotency where possible

Small example:

```python
from pydantic import BaseModel


class LookupIngredientInput(BaseModel):
    ingredient: str


class LookupIngredientOutput(BaseModel):
    sodium_mg: int
    sugar_g: float


def lookup_ingredient_tool(payload: LookupIngredientInput) -> LookupIngredientOutput:
    record = ingredient_catalog_lookup(payload.ingredient)
    return LookupIngredientOutput(
        sodium_mg=record.sodium_mg,
        sugar_g=record.sugar_g,
    )
```

The registry entry should declare scopes, sensitivity, and side effects alongside the callable.

## How to Integrate New Data Sources
Examples:
- PubMed
- local clinical databases
- nutritional reference datasets
- external health APIs

Required approach:
1. Define source trust and ownership.
2. Add ingestion adapter.
3. Normalize records into internal contracts.
4. Store provenance metadata.
5. Add embedding/indexing path if the source is part of the RAG system.
6. Add tests for malformed or partial source data.
7. Document licensing, security, and refresh cadence.

Security requirements:
- never hardcode secrets
- never expose raw provider responses directly to the UI without validation
- review PII and compliance implications before adding persistent ingestion

Small example:

```python
class PubMedRecord(BaseModel):
    source_id: str
    title: str
    abstract: str
    url: str


def normalize_pubmed_record(raw: dict[str, object]) -> PubMedRecord:
    return PubMedRecord(
        source_id=str(raw["uid"]),
        title=str(raw["title"]),
        abstract=str(raw.get("abstract", "")),
        url=f"https://pubmed.ncbi.nlm.nih.gov/{raw['uid']}/",
    )
```

After normalization:
- persist provenance
- chunk and embed if the source participates in RAG
- keep retrieval-time citations tied to the original `source_id`

## Testing Guidelines
### Required Coverage
Every meaningful change should include the right test level:
- unit tests for local logic and rules
- integration tests for API and orchestration behavior
- e2e tests for critical frontend journeys when UI behavior changes materially

### Standard Commands
Backend and full-stack validation:

```bash
uv run ruff check .
uv run ty check . --extra-search-path src --output-format concise
uv run pytest -q
pnpm web:lint
pnpm web:typecheck
pnpm --dir apps/web test:e2e
uv run python scripts/dg.py test comprehensive
```

### Prompt and Agent Regression Testing
For agentic changes, add stable regression coverage around:
- prompt assembly inputs
- output contracts
- retrieval/citation structure when applicable
- safety decisions and fallback behavior

If prompts change behavior materially, document why the change is acceptable.

Small example:

```python
def test_knowledge_agent_returns_citations() -> None:
    retrieval = FakeRetrievalService([FakeDocument(source_id="pubmed:123")])
    agent = KnowledgeRetrievalAgent(retrieval)

    result = agent.run(KnowledgeAgentInput(question="What is LDL?", user_id="user-1"))

    assert result.citations == ["pubmed:123"]
```

## Security and Safety
### Input Validation
- validate all external input at transport and business boundaries
- reject malformed or ambiguous payloads early

### Prompt Injection Mitigation
- treat retrieved content and user content as untrusted
- separate instructions from retrieved evidence
- do not allow arbitrary tool invocation from untrusted content
- preserve allowlists for tool access and workflow routing

### Access Control
- use action-based policy checks
- do not introduce role-name shortcuts in route handlers
- keep household and user-scoped access semantics explicit

### PII Handling
- store only what is needed
- redact sensitive fields from logs and telemetry
- avoid using production user data in tests or fixtures

### Medical / Wellness Safety
- do not present speculative medical claims as facts
- preserve escalation and refusal behavior where safety rules require it
- keep recommendation and emotional-support outputs within defined product boundaries

## Code Ownership and Escalation
Current ownership model should be treated as:
- API / auth / policy: backend maintainers
- frontend UX and typed client contracts: web maintainers
- orchestration, agent behavior, and safety: AI systems maintainers
- deployment/runtime/CI: platform maintainers

If formal CODEOWNERS is added later, this document should align with it.

## Documentation Maintenance
Documentation updates are required when behavior or architecture changes.

Primary index:
- `docs/README.md`

Core docs:
- `docs/system-overview.md`
- `docs/codebase-walkthrough.md`
- `docs/developer-guide.md`
- `docs/user-manual.md`
- `docs/operations-runbook.md`
- `docs/glossary.md`

Canonical references that must stay consistent:
- `ARCHITECTURE.md`
- `docs/config-reference.md`
- `docs/roadmap-v1.md`
- `docs/feature-audit.md`

Minimum rule:
- if a PR changes architecture, runtime commands, APIs, workflows, or user-facing flows, update relevant docs in the same PR.

Escalate early when a change affects:
- authentication or authorization semantics
- safety behavior
- database schema compatibility
- workflow event contracts
- external provider usage or data retention behavior

## Contributor Checklist
Before opening a PR, confirm all of the following:
- architecture boundaries are respected
- types are updated
- tests cover changed behavior
- logs and failures remain diagnosable
- docs are updated if contracts or workflows changed
- no secrets or local-only files are staged

## Guidance for AI Agents Contributing to This Repository
AI agents modifying this repository should:
- prefer thin routers and typed services
- avoid introducing hidden coupling between layers
- keep changes scoped and reviewable
- add or update tests before implementation when behavior changes
- avoid destructive git operations
- treat roadmap and architecture docs as constraints, not optional suggestions
