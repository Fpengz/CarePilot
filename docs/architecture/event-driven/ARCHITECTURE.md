# Architecture: Event-Driven Multi-Agent System (CarePilot-Aligned)

## Overview

CarePilot implements a hybrid architecture:

- Feature-first modular monolith
- Workflow orchestration via `LangGraph`
- Event-driven coordination via Domain Events + Timeline
- Agent layer for reasoning (`pydantic_ai` via `src/care_pilot/agent/runtime/**`)
- Deterministic services for execution

This is not a pure event-bus system. It follows:

Event Timeline + Workflows + Agents + Services

## Core Principles

1. Events represent facts that happened, not commands.
2. Agents are stateless reasoning modules.
3. Features and workflows own execution and side effects.
4. Supervisor logic lives in workflows and feature orchestrators.
5. State is centralized in `PatientCaseSnapshot`.
6. The system must be auditable and replayable.

## System Layers

### 1. Interface Layer

- `apps/api/carepilot_api/**`
- Receives user input
- Triggers feature flows

### 2. Feature Layer (Primary Control)

Located in:

```
src/care_pilot/features/**
```

Responsibilities:

- Business logic
- Orchestration (deterministic)
- Workflow execution
- State mutation

### 3. Workflow Layer (`LangGraph`)

Used for:

- Multi-step journeys
- Typed workflow state
- Retry and branching logic

This is the primary orchestrator for declared product flows.

### 4. Agent Layer

Located in:

```
src/care_pilot/agent/**
```

Responsibilities:

- Interpretation
- Reasoning
- Synthesis

Agents do not write state and do not call services directly.

### 5. Event Timeline Layer

Backed by:

- Domain events (`src/care_pilot/core/events.py`)
- Timeline storage
- Outbox pattern

Events represent state changes that occurred.

### 6. Execution Layer (Services)

Located in feature modules, for example:

- `src/care_pilot/features/companion/core/companion_core_service.py`
- `src/care_pilot/features/reminders/notifications/**`
- `src/care_pilot/features/reminders/outbox/**`
- `src/care_pilot/features/meals/workflows/**`

Responsibilities:

- DB writes
- Scheduling
- Notifications
- External integrations

## Control Flow Pattern

User Action → Feature → Workflow → Agents → Decision → Services → Event → Timeline

## Key Pattern

Agents propose → Features decide → Services execute

## References

- [Four Design Patterns for Event-Driven, Multi-Agent Systems](https://www.confluent.io/blog/event-driven-multi-agent-systems/)
- [A Distributed State of Mind: Event-Driven Multi-Agent Systems](https://seanfalconer.medium.com/a-distributed-state-of-mind-event-driven-multi-agent-systems-226785b479e6)
- [OpenAgents Architecture](https://openagents.org/docs/concepts/architecture)
