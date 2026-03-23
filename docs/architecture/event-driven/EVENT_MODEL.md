# Event Model (Domain Events + Timeline)

## Overview

CarePilot uses domain events, not a generic event bus.

Events:

- Represent facts that occurred
- Are immutable
- Are persisted in the timeline
- Are processed via outbox + workers

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

## Important Rule

Events do not trigger logic directly. They are consumed by workflows and services that already own orchestration.
