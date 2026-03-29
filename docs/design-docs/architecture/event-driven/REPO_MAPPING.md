# Repository Mapping (CarePilot)

## Overview

This maps the current codebase to architecture roles.

## API Layer

Path:

```
apps/api/carepilot_api/**
```

Role:

- Interface layer
- Request handling
- Policy enforcement

## Worker Layer

Path:

```
apps/workers/**
```

Role:

- Async processing
- Outbox consumption
- Scheduled execution

## Feature Layer

Path:

```
src/care_pilot/features/**
```

Role:

- Business logic
- Orchestration and decisions
- State mutation

## Workflow Orchestration

Path:

```
src/care_pilot/features/**/workflows/**
```

Role:

- `LangGraph` workflows
- Typed state transitions
- Explicit multi-step journeys

## Agent Layer

Path:

```
src/care_pilot/agent/**
```

Role:

- Reasoning and interpretation
- Structured proposals

## Agent Runtime

Path:

```
src/care_pilot/agent/runtime/**
```

Role:

- Inference execution
- Provider routing
- Runtime plumbing

## Platform Layer

Path:

```
src/care_pilot/platform/**
```

Role:

- Infrastructure
- Persistence adapters
- Messaging/outbox utilities

## Example Mapping Table

| Component Role | Example Module |
| --- | --- |
| Feature orchestration | `src/care_pilot/features/companion/core/companion_core_service.py` |
| Chat orchestration | `src/care_pilot/features/companion/chat/orchestrator.py` |
| Meal workflow | `src/care_pilot/features/meals/workflows/**` |
| Message delivery orchestration | `src/care_pilot/features/reminders/notifications/**` |
| Outbox integration | `src/care_pilot/platform/messaging/**` |
| Agent contracts | `src/care_pilot/agent/core/base.py` |

## Key Insight

CarePilot already implements the orchestrator-worker pattern, event timeline, and modular features. This spec formalizes and documents those choices.
