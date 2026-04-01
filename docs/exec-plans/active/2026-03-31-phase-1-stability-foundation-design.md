# Design Doc: Phase 1 Stability Foundation (Observability Pillar)

## Overview
Phase 1 of the CarePilot Strategic Architecture focuses on building a "Stability Foundation." This design doc specifically addresses the **Observability Pillar**, moving from fragmented logging and print statements to a unified, intrinsic observability layer using **Logfire**.

## Architecture
We will unify observability across all CarePilot entry points (API, Background Workers, Inference Layer, and CLI) using a single `logfire` configuration root. This ensures a consistent trace ID (Correlation ID) flows through the entire system, from user request to background task.

## Components
- **Unified Config**: Centralize logfire initialization in `src/care_pilot/platform/observability/setup.py`.
- **FastAPI Middleware**: Auto-instrumentation for all HTTP requests/responses, capturing latencies and status codes.
- **SQLModel/SQLAlchemy Integration**: Instrumenting the database engine to track query performance and slow queries.
- **HTTPX Instrumentation**: Capturing all outbound API calls (e.g., to LLM providers or medical databases).
- **Pydantic-AI Instrumentation**: Deep tracing into agent reasoning steps and tool calls.

## Data Flow
1.  **Ingress**: FastAPI middleware starts a trace and binds the `request_id`.
2.  **Processing**: Each layer (Feature, Agent, Platform) contributes spans to the active trace.
3.  **Persistence**: SQLModel engine emits spans for all DB interactions.
4.  **Egress**: Traces are collected and sent to the Logfire dashboard (with OTLP export support).

## Error Handling
- Use `logfire.exception()` for all caught exceptions in the workflow to capture the full stack trace and local variables.
- Standardize on structured logs (no more `print()`) to ensure logs are searchable and actionable.

## Testing & Validation
- Functional tests will verify that spans are correctly created for core business logic (Meal/Medication ingestion).
- Automated check: `grep -r "print(" src/` must return zero results in the final Phase 1 state.

## Implementation Priorities (Phase 1)
1.  **Observability Setup**: Configure logfire and instrument FastAPI/SQLModel/HTTPX.
2.  **Log Consolidation**: Replace all `print()` and standard `logging` with `logfire`.
3.  **Config Centralization**: (Subsequent task) Transition to `pydantic-settings` to manage logfire tokens and environment flags.
4.  **Async I/O Refactor**: (Subsequent task) Move to async DB sessions and HTTP clients.
