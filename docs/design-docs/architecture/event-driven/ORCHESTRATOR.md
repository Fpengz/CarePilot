# Orchestration Model (CarePilot)

## Overview

CarePilot does not use a single orchestrator. Orchestration is distributed across:

1. `LangGraph` workflows
2. Feature orchestrators
3. Service-level coordination

## Primary Orchestrators

### 1. Workflow Orchestrators

- Implemented using `LangGraph`
- Handle multi-step flows
- Maintain typed state transitions

### 2. Feature Orchestrators

Example:

```
src/care_pilot/features/companion/chat/orchestrator.py
```

Responsibilities:

- Interpret user input
- Call agents
- Merge outputs
- Trigger services

## Flow Pattern

1. Receive input
2. Load `PatientCaseSnapshot`
3. Select agents
4. Run agents
5. Merge outputs
6. Apply policy rules
7. Call services
8. Emit events

## Decision Layer

Implemented in deterministic feature logic and safety/policy services.

Responsibilities:

- Resolve conflicts
- Enforce safety
- Prioritize actions

## Key Rule

Agents do not orchestrate. Features and workflows orchestrate.

## Foreground Invariant

The foreground response must be **fully correct without any background agent output**.
Background results only enrich later turns and must never repair a missing core answer.

## Background Agent Rules

Background agents may only write:

- Cached advisory outputs
- Summarized insights
- Candidate recommendations awaiting standard workflow ingestion

They must not mutate core clinical state directly.

## Freshness Windows

Deferred outputs should include TTLs:

- Emotion deep analysis: short TTL
- Adherence synthesis: medium TTL
- Long-term trends: longer TTL

## Why Not Pure Event-Driven

Pure event choreography increases implicit flows and complicates auditing. CarePilot uses explicit orchestration to keep traceability, auditability, and compliance first.
