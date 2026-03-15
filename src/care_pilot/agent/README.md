# Agent Layer

This package contains bounded, model-powered capabilities. It is **not** the
business orchestration layer and it does not own durable state.

## Structure

- `core/`: canonical agent contracts (`BaseAgent`, `AgentContext`, `AgentResult`, registry)
- `runtime/`: inference plumbing and model routing
- `dietary/`, `meal_analysis/`, `recommendation/`, `emotion/`, `chat/`: bounded agent packages

## Rules

- Each agent package exposes one public entrypoint (`<AgentName>Agent`).
- Cross-cutting runtime logic belongs in `runtime/`, not in agent packages.
- Business orchestration belongs in `features/`, not here.
- Agents must not write durable state directly.
