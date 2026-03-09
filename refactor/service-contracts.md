# Service Contracts

## Purpose

This document defines the initial service boundaries and high-level contracts for the clean-slate platform.

These are not code-level OpenAPI files. They are the architectural contracts engineering should use before implementation.

## Boundary Rules

- Public clients talk only to the `Experience Gateway`.
- Internal services communicate through typed APIs and event schemas.
- Agents are invoked only by the `Care Orchestrator`.
- Only the `Care Orchestrator` and `Workflow Engine` may trigger state transitions across multiple services.

## Public Synchronous APIs

### `POST /v1/interactions`

Purpose:

- main entry point for chat turns, meal review requests, voice/text questions, check-in answers, and symptom concerns

Request:

```json
{
  "user_id": "usr_123",
  "channel": "web",
  "thread_id": "thr_456",
  "interaction_type": "chat_message",
  "message": {
    "text": "Can eat or not? This char kway teow got hum and quite oily"
  },
  "attachments": [
    {
      "type": "image",
      "purpose": "meal_photo"
    }
  ],
  "context": {
    "locale": "en-SG",
    "timezone": "Asia/Singapore",
    "app_surface": "chat"
  }
}
```

Response:

```json
{
  "interaction_id": "int_789",
  "response_mode": "guidance_with_follow_up",
  "content": {
    "title": "You can still eat this, but adjust it",
    "body": "Ask for less hum and no extra lard, then stop at about half the noodles if you want a safer option.",
    "actions": [
      {
        "type": "log_meal_portion",
        "label": "Log safer portion"
      }
    ]
  },
  "metadata": {
    "risk_level": "medium",
    "evidence_confidence": "moderate",
    "follow_up_required": true,
    "human_escalation_recommended": false
  }
}
```

### `POST /v1/meal-analyses`

Purpose:

- analyze meal images or meal descriptions into structured meal events and localized dietary guidance

Request:

```json
{
  "user_id": "usr_123",
  "input": {
    "image_id": "img_456",
    "text_hint": "char kway teow"
  },
  "context": {
    "locale": "en-SG",
    "timezone": "Asia/Singapore"
  }
}
```

Response:

```json
{
  "meal_analysis_id": "meal_001",
  "meal_event": {
    "dish_name": "char kway teow",
    "food_tags": [
      "hawker",
      "high_sodium",
      "high_refined_carb"
    ]
  },
  "guidance": {
    "summary": "Reduce portion and request less added fat.",
    "localized_substitutions": [
      "eat half the noodles",
      "skip extra cockles if trying to reduce risk"
    ]
  }
}
```

### `POST /v1/observations`

Purpose:

- create structured observations such as symptoms, vitals, meals, habits, medication adherence, or self-reported metrics

Request:

```json
{
  "user_id": "usr_123",
  "observation_type": "blood_glucose",
  "value": {
    "numeric": 152,
    "unit": "mg/dL"
  },
  "observed_at": "2026-03-09T08:30:00+08:00",
  "source": "manual_entry",
  "context": {
    "meal_relation": "after_breakfast"
  }
}
```

Response:

```json
{
  "observation_id": "obs_001",
  "workflow_triggered": true,
  "workflow_ids": [
    "wf_glucose_followup_01"
  ]
}
```

### `POST /v1/reports/parse`

Purpose:

- extract structured biomarker updates from uploaded reports or PDFs

Request:

```json
{
  "user_id": "usr_123",
  "report_file_id": "file_789",
  "report_type": "lab_report"
}
```

Response:

```json
{
  "report_artifact_id": "rep_001",
  "biomarker_updates": [
    {
      "type": "hba1c",
      "value": 7.5,
      "unit": "%"
    }
  ]
}
```

### `POST /v1/workflows/{workflow_id}/actions`

Purpose:

- progress a durable workflow with a user answer or system action

Request:

```json
{
  "action_type": "submit_answer",
  "payload": {
    "question_id": "symptom_duration",
    "answer": "3 days"
  }
}
```

Response:

```json
{
  "workflow_id": "wf_symptom_01",
  "status": "in_progress",
  "next_step": {
    "type": "question",
    "prompt": "Are you also experiencing fainting, chest pain, or trouble breathing?"
  }
}
```

## Internal Service APIs

### Care Orchestrator -> Profile and Case Service

Method:

- `GetCaseSnapshot(user_id, thread_id, intent_hint?)`

Response shape:

```json
{
  "user": {},
  "care_profile": {},
  "conditions": [],
  "medications": [],
  "goals": [],
  "recent_observations": [],
  "active_workflows": [],
  "risk_state": {},
  "behavioral_profile": {},
  "consent_state": {}
}
```

### Care Orchestrator -> Knowledge and Evidence Service

Method:

- `RetrieveEvidence(task_type, condition_tags, audience, query, limit)`

Response shape:

```json
{
  "evidence_items": [
    {
      "evidence_id": "ev_1",
      "title": "Recognizing hypoglycemia symptoms",
      "summary": "Dizziness and sweating may require prompt action depending on severity.",
      "confidence": "high",
      "source_type": "guideline_pack",
      "source_version": "v2026.02"
    }
  ]
}
```

### Knowledge and Evidence Service -> EvidenceRetrievalPort

Purpose:

- isolate the platform from the concrete retrieval backend

Methods:

- `SearchEvidence(query, filters, limit)`
- `FetchEvidenceByIds(evidence_ids)`

Hackathon adapter:

- `ChromaEvidenceStore`

Scale-later adapter:

- `PgVectorEvidenceStore`

Normalized response shape:

```json
{
  "items": [
    {
      "evidence_id": "ev_1",
      "chunk_id": "ch_01",
      "text": "Recognizing hypoglycemia symptoms and when to seek help.",
      "score": 0.88,
      "source_id": "src_guideline_12",
      "source_version": "v2026.02",
      "tags": [
        "diabetes",
        "symptoms"
      ]
    }
  ]
}
```

### Care Orchestrator -> Capability Services

Representative methods:

- `ComputeRiskState(case_snapshot)`
- `ExtractSymptoms(interaction)`
- `ScoreAdherence(user_id, horizon)`
- `RankRecommendations(case_snapshot, evidence_items)`
- `PlanReminder(candidate_action, user_preferences)`

Capability outputs must always be deterministic and versioned.

### Care Orchestrator -> Personalization Engine

Methods:

- `BuildPersonalizationContext(case_snapshot, recent_inputs, channel_context)`

Response shape:

```json
{
  "risk_modifiers": [
    "type_2_diabetes",
    "high_recent_sodium"
  ],
  "behavioral_modifiers": [
    "often_eats_outside_home"
  ],
  "content_preferences": {
    "language_style": "plain_singlish_friendly"
  }
}
```

### Care Orchestrator -> Engagement Intelligence Service

Methods:

- `ScoreEngagementState(user_id, horizon)`
- `RankProactiveOutreach(user_id, case_snapshot)`

Response shape:

```json
{
  "engagement_risk_level": "medium",
  "nudge_candidate": "post_meal_walk_prompt",
  "follow_up_priority": "high"
}
```

### Care Orchestrator -> Agent Runtime

Method:

- `RunAgent(agent_name, input, policy_profile, tool_allowlist, schema_version)`

Generic response shape:

```json
{
  "agent_run_id": "ar_001",
  "agent_name": "CarePlanningAgent",
  "output": {},
  "confidence": 0.84,
  "latency_ms": 910,
  "model_version": "model_x",
  "prompt_version": "care-planner-v3"
}
```

### Care Orchestrator -> Safety and Policy Service

Method:

- `ReviewCandidateResponse(candidate_plan, case_snapshot, evidence_items, policy_context)`

Response shape:

```json
{
  "decision": "allow_with_downgrade",
  "risk_level": "medium",
  "policy_actions": [
    "remove_speculative_claim",
    "add_red_flag_disclaimer"
  ],
  "escalation": null
}
```

### Care Orchestrator -> Clinician Copilot Summary Service

Methods:

- `BuildClinicianDigest(user_id, time_window, trigger_reason)`

Response shape:

```json
{
  "digest_id": "dig_001",
  "summary": "Meal risk and adherence have worsened over the last 7 days.",
  "priority": "high",
  "suggested_actions": [
    "review sodium-heavy meal pattern",
    "check medication adherence"
  ]
}
```

### Care Orchestrator -> Impact Measurement Service

Methods:

- `ComputeImpactMetrics(subject_id, metric_window, metric_profile)`

Response shape:

```json
{
  "adherence_rate": 0.82,
  "meal_risk_improvement": 0.18,
  "nudge_acceptance_rate": 0.56,
  "clinician_time_saved_minutes": 12
}
```

## Agent Output Schemas

### IntentContextAgent

```json
{
  "intent": "symptom_concern",
  "sub_intents": [
    "possible_post_meal_pattern"
  ],
  "confidence": 0.91,
  "requires_follow_up_questions": true,
  "risk_hints": [
    "dizziness"
  ]
}
```

### CarePlanningAgent

```json
{
  "plan_type": "question_sequence",
  "recommended_actions": [
    {
      "type": "ask_question",
      "question_key": "symptom_severity"
    }
  ],
  "user_message_draft": "I want to rule out anything urgent first."
}
```

### EvidenceSynthesisAgent

```json
{
  "user_explanation": "Dizziness after eating can happen for several reasons, including blood sugar changes.",
  "citations": [
    "ev_1"
  ],
  "reading_level": "plain_language"
}
```

### MotivationalSupportAgent

```json
{
  "tone_profile": "calm_supportive",
  "coaching_message": "You do not need to figure this out all at once. We can take it step by step.",
  "engagement_action": "encourage_follow_up"
}
```

### SafetyReviewAgent

```json
{
  "concerns": [
    "needs_red_flag_screening"
  ],
  "decision_hint": "downgrade_until_more_info",
  "required_follow_up": [
    "ask_emergency_symptoms"
  ]
}
```

## Event Contracts

## Event Bus Topics

- `interaction.received`
- `observation.recorded`
- `risk.updated`
- `workflow.started`
- `workflow.step.completed`
- `workflow.timer.fired`
- `agent.run.completed`
- `policy.review.completed`
- `response.delivered`
- `reminder.sent`
- `reminder.missed`
- `escalation.created`

### Example Event: `observation.recorded`

```json
{
  "event_id": "evt_1",
  "aggregate_type": "user",
  "event_type": "observation.recorded",
  "occurred_at": "2026-03-09T08:31:00+08:00",
  "causation_id": "cmd_record_observation_1",
  "correlation_id": "corr_123",
  "actor_type": "user",
  "actor_id": "usr_123",
  "schema_version": "1.0",
  "aggregate_id": "usr_123",
  "payload": {
    "observation_id": "obs_001",
    "observation_type": "blood_glucose",
    "source": "manual_entry",
    "workflow_trigger_candidates": [
      "glucose_followup"
    ]
  }
}
```

### Example Event: `policy.review.completed`

```json
{
  "event_id": "evt_2",
  "aggregate_type": "interaction",
  "event_type": "policy.review.completed",
  "occurred_at": "2026-03-09T08:31:01+08:00",
  "causation_id": "cmd_review_response_1",
  "correlation_id": "corr_123",
  "actor_type": "service",
  "actor_id": "safety_policy_service",
  "schema_version": "1.0",
  "aggregate_id": "int_789",
  "payload": {
    "policy_decision_id": "pd_001",
    "decision": "allow_with_downgrade",
    "risk_level": "medium",
    "policy_actions": [
      "require_follow_up_questions"
    ]
  }
}
```

## Contract Design Rules

- every contract is versioned
- outputs are typed and machine-readable
- agents return proposals, never final authority
- policy decisions are explicit artifacts, not implicit text
- event payloads should be append-only compatible once published
