# Event Timeline Coverage Map

This document tracks event timeline coverage for key CarePilot workflows as part
of the event-driven multi-agent refactor. It focuses on events appended via
`EventTimelineService` and `WorkflowTraceEmitter`.

## Coverage Matrix

| Workflow / Flow | Event Types Emitted | Notes |
| --- | --- | --- |
| Companion chat (LangGraph) | `workflow_started`, `agent_action_proposed`, `workflow_completed`, `workflow_failed` | Emitted in `features/companion/chat/orchestrator.py`. |
| Meal analysis (LangGraph) | `workflow_started`, `workflow_completed`, `meal_analyzed`, `meal_confirmed`, `meal_skipped`, `agent_action_proposed` | Includes arbitration + dietary proposal events and agent proposal when text is present. |
| Medication intake (text/upload) | `workflow_started`, `workflow_completed`, `medication_logged`, `reminder_scheduled`, `agent_action_proposed` | Intake flows emit start/complete via trace emitter plus medication agent proposals. |
| Medication intake confirm | `workflow_started`, `workflow_completed` | Emitted when draft is confirmed into regimens/reminders. |
| Medication regimen (manual create) | `medication_logged` | Logged on regimen creation. |
| Medication regimen updates | `medication_updated`, `medication_deleted` | Emitted on regimen patch/delete. |
| Medication adherence | `adherence_updated` | Logged on adherence event creation. |
| Symptom check-in | `symptom_reported` | Emitted on symptom check-in creation. |
| Profile updates | `profile_updated`, `profile_onboarding_step`, `profile_onboarding_completed` | Emitted on profile updates and onboarding progress. |
| Household lifecycle | `household_created`, `household_renamed`, `household_invite_created`, `household_joined`, `household_member_removed`, `household_left` | Emitted on household CRUD and membership events. |
| Reminder generation | `workflow_started`, `workflow_completed` | Emits when reminders are generated. |
| Reminder alert (alert_only) | `workflow_started`, `reminder_triggered`, `workflow_completed` | Alert flow emits reminder-triggered timeline event. |
| Reminder confirmation | `reminder_confirmed` | Logged when a user confirms or skips a reminder. |
| Reminder materialization | `reminder_scheduled` | Emitted when scheduled notifications are created. |
| Recommendation daily agent | `workflow_started`, `agent_action_proposed`, `workflow_completed` | Timeline events emitted around agent generation. |
| Recommendation generate (single record) | `workflow_started`, `workflow_completed` | Emitted for standard recommendation flow. |
| Recommendation substitution | `workflow_started`, `workflow_completed` | Emits request-level timeline events. |
| Recommendation interaction | `workflow_started`, `workflow_completed` | Emits interaction-level timeline events. |
| Report parse | `workflow_started`, `workflow_completed` | Report parsing already emits timeline events. |
| Snapshot projections (sectioned) | Rebuildable via projection handlers | Per-section projectors update materialized snapshot fields with ordering scope `per_patient` and replay via `scripts/cli.py projections replay`. |
| Reaction handlers (async) | Execution records in `event_reaction_executions` | Ordered per handler’s `ordering_scope` (global/per_patient/per_case/none) with cursored replay safeguards. |

## Gaps / Follow-Ups

- None currently identified for critical paths. Continue to audit newly added workflows for event coverage.
- Audit note (2026-03-22): workflow start/complete events present for all currently tracked flows.

## Replay Determinism Test

- Projector rebuild from full event history should match incremental projection output.

## Agent Invocation Audit
- [ ] `src/care_pilot/features/companion/chat/orchestrator.py:150` — emotion inference (`infer_text`)
- [ ] `src/care_pilot/features/companion/chat/orchestrator.py:414` — emotion inference (`infer_speech`)
- [ ] `src/care_pilot/features/companion/chat/workflows/companion_graph.py:84` — supervisor routing (`run_supervisor_agent`)
- [ ] `src/care_pilot/features/meals/use_cases/confirm_meal.py:88` — dietary agent adapter invocation
- [ ] `src/care_pilot/features/meals/workflows/meal_upload_graph.py:112` — meal agent proposal invocation
- [ ] `src/care_pilot/features/medications/medication_management.py:726` — medication agent proposal invocation
- [ ] `src/care_pilot/features/recommendations/recommendation_service.py:420` — recommendation agent adapter invocation
