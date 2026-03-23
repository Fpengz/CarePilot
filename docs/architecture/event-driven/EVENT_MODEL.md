# Event Model (Domain Events + Timeline)

## Overview

CarePilot uses domain events, not a generic event bus.

Events:

- Represent facts that occurred
- Are immutable
- Are persisted in the timeline
- Are processed via outbox + workers

## Three Event Concepts (Explicit Separation)

CarePilot separates three concepts to keep replay safe and coupling low:

1. **Domain Events (facts)**  
   Immutable records of what happened (e.g., `meal.analyzed`, `medication.logged`). These are the audit log and replay source.

2. **Projections (derived state maintenance)**  
   Deterministic handlers that materialize state (e.g., `patient_case_snapshot`).  
   Projectors must be deterministic, versioned, replayable, and should avoid external network calls.

3. **Reactions (async side effects / enrichments)**  
   Optional async work triggered by domain events (e.g., notifications, background agent insights).  
   Reactions are idempotent and tolerate retries.

## Event Schema

Defined in:

```
src/care_pilot/core/events.py
```

```python
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
```

## Key Principle

Events describe what happened, not what should happen.

## Event Categories

### 1. User Events

- user.message.sent
- meal.uploaded

### 2. Domain Events

- meal.analyzed
- medication.logged
- adherence.updated

### 3. Workflow Events

- workflow.started
- workflow.completed

### 4. System Events

- reminder.triggered
- notification.sent

## Timeline

Events are stored in timeline tables and audit logs. They are used for:

- Debugging
- Replay
- Analytics
- Personalization

## Outbox Pattern

Events are:

1. Written transactionally with domain changes
2. Processed asynchronously by workers

Benefits:

- Reliability
- No lost events
- Decoupled execution

**Important:** The outbox is about **reliable async side effects after a successful write** (transactional consistency), not about replacing the timeline or projections.

## Reaction Handler Contract (Conceptual)

Reactions are async handlers with explicit delivery and ordering semantics:

```python
class ReactionHandler(Protocol):
    delivery_semantics: Literal["at_least_once"]
    ordering_scope: Literal["global", "per_patient", "per_case", "none"]
    name: str
```

## Idempotency Execution Record (Conceptual)

Each reaction execution should persist:

- `event_id`
- `handler_name`
- `status`
- `started_at`
- `completed_at`
- `failure_count`
- `last_error`
- `payload_hash`
- `event_version`

## Important Rules

- **Domain events** are facts that happened.
- **Projections** maintain derived state deterministically.
- **Reactions** are optional enrichments and must be idempotent.

## References

- [AWS Event Sourcing pattern (auditability & replay)](https://aws-samples.github.io/eda-on-aws/patterns/event-sourcing/)
- [AWS Transactional Outbox pattern (reliable async side effects)](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
