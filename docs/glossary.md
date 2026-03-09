# Glossary

Last updated: 2026-03-06

## Architecture Terms
- API Layer: FastAPI transport surface that validates requests and enforces access policies.
- Orchestration Layer: Services coordinating workflows across agents/tools and state.
- Agent: Specialized logic unit performing reasoning or task-specific processing.
- Tool Registry: Controlled mechanism for invoking side-effectful tools with policy checks.
- Worker: Process handling asynchronous jobs (reminders, notifications, scheduling).

## Workflow Terms
- Workflow: Ordered sequence of actions for a domain task (meal analysis, report parse, replay).
- Correlation ID: Identifier linking related events across one logical workflow execution.
- Request ID: Identifier for a single inbound API request.
- Timeline Event: Structured event appended during workflow execution/replay.
- Replay: Read-only reconstruction of prior workflow events by correlation ID.

## Governance Terms
- Runtime Contract: Declared workflow-step and agent/tool capability mapping exposed by API.
- Runtime Contract Snapshot: Versioned persisted copy of runtime contract state.
- Tool Policy: Role/agent/tool rule controlling allow/deny decisions.
- Shadow Mode: Policy evaluated and reported without enforcing deny behavior.
- Enforce Mode: Policy evaluation affects effective tool decision.

## Data and Storage Terms
- Durable State: Persisted domain state in SQLite/Postgres stores.
- Ephemeral State: Short-lived cache/coordination state (in-memory or Redis).
- Outbox: Durable record of side effects queued for asynchronous delivery.
- Redis Keyspace: Canonical Redis key naming scheme used by cache and coordination stores.

## Product Terms
- Health Profile: User baseline and constraints used for personalization.
- Meal Summary: Daily/weekly nutrition aggregates and insights.
- Adherence Event: Medication status event (`taken`, `missed`, `skipped`, `unknown`).
- Symptom Check-In: User-reported symptom severity/codes/free text plus safety metadata.
- Clinical Card: Structured clinician-facing summary with sections and trends.

## Operational Terms
- Readiness: API health check result with dependency-aware status (`ready`, `degraded`, `not_ready`).
- Smoke Test: End-to-end operational verification of core runtime paths.
- Comprehensive Test: Full validation gate across lint/type/tests/build/e2e/smoke.
