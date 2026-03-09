# Data Model

## Purpose

Define the canonical domain entities, event model, and storage strategy for the refactored platform.

## Modeling Principles

- use typed domain entities for durable facts
- treat event history as first-class
- separate health facts from conversational memory
- allow new conditions and workflows without schema collapse
- optimize read models for orchestration, not for raw storage purity

## Primary Entity Groups

### Identity and Access

- `User`
- `Household`
- `CaregiverLink`
- `ConsentRecord`
- `ChannelIdentity`

### Health Profile

- `CareProfile`
- `Condition`
- `Medication`
- `Allergy`
- `CareGoal`
- `RiskState`
- `PersonalizationContext`
- `EngagementState`

### Health Signals

- `MealEvent`
- `MealAnalysis`
- `FoodItemCandidate`
- `Observation`
- `LabResult`
- `ReportArtifact`
- `BiomarkerUpdate`
- `MealRecord`
- `SymptomReport`
- `AdherenceRecord`

### Interaction and Workflow

- `ConversationThread`
- `Interaction`
- `WorkflowDefinition`
- `WorkflowInstance`
- `WorkflowStep`
- `Reminder`
- `Escalation`

### Intelligence and Policy

- `EvidenceReference`
- `RecommendationArtifact`
- `PolicyDecision`
- `AgentRun`
- `PromptVersion`
- `ClinicianDigest`
- `ImpactMetricSnapshot`

## Canonical Entity Notes

### `CareProfile`

Purpose:

- current durable summary of user health and support context

Representative fields:

- `user_id`
- `date_of_birth`
- `sex_at_birth` if collected
- `conditions`
- `medications`
- `allergies`
- `baseline_risk_tier`
- `goals`
- `preferred_language`
- `health_literacy_level`
- `caregiver_links`

### `Observation`

Purpose:

- universal typed record for health-relevant signals

Representative fields:

- `observation_id`
- `user_id`
- `type`
- `value_numeric`
- `value_text`
- `unit`
- `observed_at`
- `source`
- `confidence`
- `context_json`

Examples:

- blood pressure
- glucose
- sleep duration
- weight
- symptom intensity
- stress score
- medication taken

### `MealEvent`

Purpose:

- normalized representation of a meal inferred from image, text, voice, or manual logging

Representative fields:

- `meal_event_id`
- `user_id`
- `dish_name`
- `food_items_json`
- `portion_estimate`
- `meal_time`
- `input_source`
- `localization_tags`

### `ReportArtifact`

Purpose:

- parsed document artifact that links uploaded reports to structured biomarker updates

Representative fields:

- `report_artifact_id`
- `user_id`
- `source_file_id`
- `report_type`
- `parsed_text_hash`
- `created_at`

### `Interaction`

Purpose:

- immutable user or system interaction record

Representative fields:

- `interaction_id`
- `thread_id`
- `user_id`
- `interaction_type`
- `input_payload`
- `output_payload`
- `response_mode`
- `risk_level`
- `created_at`

### `WorkflowInstance`

Purpose:

- durable long-running care or support journey

Representative fields:

- `workflow_instance_id`
- `workflow_type`
- `user_id`
- `status`
- `current_step`
- `started_at`
- `updated_at`
- `deadline_at`
- `state_json`

### `PolicyDecision`

Purpose:

- durable record of what policy evaluated and what it decided

Representative fields:

- `policy_decision_id`
- `subject_type`
- `subject_id`
- `policy_version`
- `decision`
- `risk_level`
- `actions_json`
- `created_at`

### `AgentRun`

Purpose:

- traceable record of a structured model invocation

Representative fields:

- `agent_run_id`
- `agent_name`
- `input_hash`
- `output_json`
- `model_version`
- `prompt_version`
- `latency_ms`
- `cost_micros`
- `created_at`

## Event Model

The event log is append-only and acts as the canonical history of decisions and state changes.

### Required Event Metadata

- `event_id`
- `event_type`
- `aggregate_type`
- `aggregate_id`
- `occurred_at`
- `causation_id`
- `correlation_id`
- `actor_type`
- `actor_id`
- `schema_version`
- `payload`

### Core Event Families

- `user.*`
- `profile.*`
- `condition.*`
- `observation.*`
- `interaction.*`
- `workflow.*`
- `risk.*`
- `policy.*`
- `agent.*`
- `response.*`
- `reminder.*`
- `escalation.*`

### Example Event Sequence

Symptom concern flow:

1. `interaction.received`
2. `risk.precheck.completed`
3. `agent.intent_context.completed`
4. `capability.symptom_extract.completed`
5. `agent.care_planning.completed`
6. `policy.review.completed`
7. `interaction.responded`
8. `workflow.started`

## Storage Strategy

### Operational Relational Store

Use for:

- current user state
- workflows
- reminders
- consent
- interactions
- policy decisions

Properties:

- transactional integrity
- queryability
- strong consistency for user-visible state

### Event Store

Use for:

- append-only domain events
- replay
- audits
- analytics backfill

Properties:

- immutable history
- partition by aggregate or user
- versioned schemas

### Cache and Queue Layer

Use for:

- short-lived conversation summaries
- distributed locks
- workflow timers
- idempotency markers
- queue signaling

### Retrieval Store

Use for:

- evidence indexing
- semantic retrieval
- content metadata joins

The retrieval backend is an implementation detail behind an internal `EvidenceRetrievalPort`.

Hackathon implementation:

- Chroma

Scale-later option:

- PostgreSQL with pgvector

## Read Models

### Case Snapshot View

Used by:

- Care Orchestrator

Contains:

- health profile
- current conditions
- medications
- recent observations
- active workflows
- recent interactions
- risk state
- consent state

### Engagement View

Used by:

- reminder planning
- adherence coaching

Contains:

- reminder response history
- check-in completion rate
- preferred time windows
- engagement fatigue indicators

### Safety View

Used by:

- Safety and Policy Service

Contains:

- latest risk tier
- active escalations
- contraindication signals
- recent red-flag observations

## Memory Separation

### Health Memory

Durable, typed, high-trust:

- conditions
- meds
- labs
- structured observations

### Behavioral Memory

Durable, lower-trust:

- coaching preference
- engagement style
- adherence friction

### Conversation Memory

Short-lived:

- recent summaries
- unresolved questions
- temporary context

Conversation memory must never be promoted to health memory without an explicit typed write path.

## Data Governance Rules

- every medically relevant fact has provenance
- inferred facts are labeled as inferred
- user-entered facts and system-derived facts are distinguished
- deletions use soft-delete or tombstone strategy where audit requires it
- all schemas are versioned
