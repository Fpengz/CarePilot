# API Contract: Suggestions (Unified Report -> Recommendation Flow)

## Summary
The suggestions API provides a single endpoint to parse report text and generate a recommendation payload, then persists the result as a suggestion record.

This is a convenience orchestration endpoint that builds on the existing lower-level APIs:
- `POST /api/v1/reports/parse`
- `POST /api/v1/recommendations/generate`

## Endpoints

### `POST /api/v1/suggestions/generate-from-report`
Generates a suggestion by:
1. parsing pasted report text
2. building a clinical snapshot
3. generating a recommendation using the latest saved meal record
4. persisting a suggestion snapshot

#### Auth / scopes
Requires both:
- `report:write`
- `recommendation:generate`

#### Request
```json
{
  "source": "pasted_text",
  "text": "HbA1c 7.1 LDL 4.2 systolic bp 150 diastolic bp 95"
}
```

#### Response (shape)
```json
{
  "suggestion": {
    "suggestion_id": "uuid",
    "created_at": "2026-02-26T00:00:00+00:00",
    "source_user_id": "user_001",
    "source_display_name": "Member",
    "disclaimer": "This information is for general wellness...",
    "safety": {
      "decision": "allow",
      "reasons": [],
      "required_actions": [],
      "redactions": []
    },
    "report_parse": {
      "readings": [{"name": "hba1c", "value": 7.1}],
      "snapshot": {"biomarkers": {"hba1c": 7.1}, "risk_flags": ["high_hba1c"]}
    },
    "recommendation": {
      "safe": true,
      "rationale": "...",
      "localized_advice": ["..."],
      "blocked_reason": null,
      "evidence": {"hba1c": 7.1}
    },
    "workflow": {
      "workflow_name": "suggestions_generate_from_report",
      "request_id": "uuid",
      "correlation_id": "uuid",
      "replayed": false,
      "timeline_events": [
        {"event_type": "workflow_started"},
        {"event_type": "workflow_completed"}
      ]
    }
  }
}
```

#### Error cases
- `400` `no meal records available` (recommendation generation currently depends on a saved meal)
- `401` authentication required / invalid session
- `403` missing required scopes

### Red-flag escalation behavior
If red-flag symptom text is detected, the endpoint returns `200` with:
- `suggestion.safety.decision = "escalate"`
- urgent-care actions in `suggestion.recommendation.localized_advice`
- `blocked_reason = "red_flag_escalation"`
- workflow timeline completion event type `workflow_escalated` (instead of `workflow_completed`)

In this path, meal records are not required.

### Workflow replay integration
Suggestions workflow events are appended to the global workflow timeline. Admin users can replay a suggestion workflow using:
- `GET /api/v1/workflows/{correlation_id}`
- timeline event payloads include `suggestion_id` for correlation across suggestion records and workflow traces

### `GET /api/v1/suggestions`
Lists persisted suggestion snapshots for the authenticated user.

#### Auth / scopes
Requires:
- `report:read`

#### Query params
- `limit` (optional, `1..100`, default `20`)
- `scope` (optional, `self|household`, default `self`)
  - `household` requires an active household and returns merged household-member suggestions.
- `source_user_id` (optional)
  - when used with `scope=household`, filters results to a specific household member user id.

### `GET /api/v1/suggestions/{suggestion_id}`
Returns one persisted suggestion snapshot for the authenticated user.

#### Auth / scopes
Requires:
- `report:read`

#### Query params
- `scope` (optional, `self|household`, default `self`)

## Notes
- Current v1 implementation stores suggestions per-user only.
- Household-shared suggestion visibility is planned for a later milestone.
- The endpoint includes a brief disclaimer to support safety/triage positioning.
