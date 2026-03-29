# Agent Contracts (CarePilot)

## Overview

Agents are stateless reasoning components.

They:

- Interpret context
- Generate structured outputs
- Propose actions

They do not:

- Mutate state
- Call services
- Persist data

## Base Interfaces

Defined in:

```
src/care_pilot/agent/core/base.py
```

Canonical contracts:

- `BaseAgent`
- `AgentContext`
- `AgentResult`

## AgentContext

`AgentContext` is request-scoped metadata passed to every agent call. It includes identifiers such as `user_id`, `session_id`, `request_id`, `correlation_id`, and timestamps.

Agent inputs should carry the substantive context, typically including:

- `PatientCaseSnapshot`
- Recent timeline events
- User input
- Feature-specific inputs

## AgentResult (Actual Envelope)

The canonical result envelope includes the following fields:

- `success`
- `agent_name`
- `output`
- `confidence`
- `rationale`
- `warnings`
- `errors`
- `raw`

This is the definitive runtime contract.

## Conceptual View (Simplified)

For readability in product docs, we sometimes describe a simplified view:

```python
class AgentResultView(BaseModel):
    summary: str
    structured_output: dict
    recommendations: list[dict]
    confidence: float
```

This conceptual view is not a runtime contract and must not replace the real envelope.

## Agent Responsibilities

| Type | Example |
| --- | --- |
| Perception | `MealAnalysisAgent` |
| Reasoning | `DietaryAgent` |
| Planning | `RecommendationAgent` |
| Interaction | `ChatAgent` |

## Example (Conceptual)

```json
{
  "summary": "High sugar intake detected",
  "structured_output": {
    "risk": "high_sugar"
  },
  "recommendations": [
    {"type": "diet", "message": "Reduce sugar intake"}
  ],
  "confidence": 0.85
}
```

## Rules

1. Agents are pure functions where possible.
2. No side effects.
3. All outputs must be structured.
4. Deterministic fallback exists in features.
