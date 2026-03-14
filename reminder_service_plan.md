# Reminder Service Plan

## Summary

This plan tracks the structured reminder refactor and its current implementation status.

Architecture alignment with `refactor_plan.md`:
- medications own regimen truth
- reminders own reminder truth
- reminder scheduling logic stays deterministic in `features/reminders/domain`
- delivery remains separated from creation and scheduling
- route handlers stay transport-only
- legacy `ReminderEvent` remains a compatibility projection during migration

## Target Model

- `ReminderDefinition`: durable reminder truth, optionally linked to a medication regimen
- `ReminderScheduleRule`: normalized schedule semantics for one-time, daily fixed times, meal-relative timing, weekdays, every-X-hours, bedtime, PRN, and temporary-course patterns
- `ReminderOccurrence`: one executable reminder instance with timing, status, and action window
- `ReminderActionRecord`: user action log such as `taken`, `skipped`, `snooze`, `ignored`, `view_details`
- `ReminderDeliveryAttempt`: delivery projection backed by scheduled notifications and notification logs
- `ReminderEvent`: compatibility read model retained for current APIs, metrics, and migration safety

## Current Progress

### Phase 1: Canonical reminder model and boundaries

Status: `mostly implemented`

Implemented:
- added structured reminder domain types in `src/dietary_guardian/features/reminders/domain/models.py`
- added deterministic generation helpers in `src/dietary_guardian/features/reminders/domain/generation.py`
- added reminder use cases in `src/dietary_guardian/features/reminders/use_cases/structured.py`
- added persistence support for:
  - `reminder_definitions`
  - `reminder_occurrences`
  - `reminder_actions`
- extended compatibility `reminder_events` with `reminder_definition_id` and `occurrence_id`
- added reminder definition APIs:
  - `GET /api/v1/reminders/definitions`
  - `POST /api/v1/reminders/definitions`
  - `PATCH /api/v1/reminders/definitions/{reminder_definition_id}`

Still open:
- richer validation for manual reminder-definition creation
- fuller write-path coverage in API tests for direct manual reminder creation/update

### Phase 2: Scheduling engine refactor

Status: `partially implemented`

Implemented:
- regimen-driven generation now creates reminder definitions and occurrences
- hybrid support exists for:
  - daily fixed times
  - meal-relative scheduling with fallback meal anchors
- default fallback anchors are encoded in generation:
  - breakfast `08:00`
  - lunch `13:00`
  - dinner `19:00`
  - bedtime `22:00`
- occurrence dedupe is enforced against existing definition/time pairs

Still open:
- first-class scheduler loop based directly on `ReminderOccurrence` leasing rather than compatibility events
- every-X-hours, weekdays, PRN, bedtime, and temporary-course occurrence generation beyond the schema/model layer
- stronger grace-window and timeout classification
- automatic missed/expired transitions

### Phase 3: Delivery and actionable notifications

Status: `partially implemented`

Implemented:
- notification payloads now carry `occurrence_id` and `reminder_definition_id`
- occurrence actions are available through:
  - `POST /api/v1/reminders/occurrences/{occurrence_id}/actions`
- supported actions currently wired:
  - `taken`
  - `skipped`
  - `snooze`
- legacy confirm API is bridged through the structured occurrence action flow

Still open:
- dedicated delivery-attempt domain model and read APIs
- structured follow-up retry policy tied to occurrence state
- full snooze rescheduling loop in background scheduling
- richer delivery action payloads across all channels

### Phase 4: Medication bridge and prescription ingest

Status: `partially implemented`

Implemented:
- regimen-driven reminder sync now creates reminder definitions and occurrences
- reminder actions create medication adherence events deterministically
- parsed medication intake continues to work with the compatibility path intact

Still open:
- move medication intake confirmation onto reminder-definition creation directly instead of relying on compatibility event generation
- make `features/medications/workflows/prescription_ingest_graph.py` the canonical bridge
- normalize more schedule patterns from parsed medication instructions:
  - every X hours
  - temporary courses
  - PRN with usage limits

### Phase 5: UI MVP

Status: `implemented`

Implemented in `apps/web/app/reminders/page.tsx`:
- Create reminder panel with manual schedule inputs
- Planned reminders list with next trigger and pause/activate
- Upcoming & history collapsed section
- Upcoming/history are read-only lists (no inline actions yet)

Manual schedule types supported in the UI:
- one-time date + time
- daily fixed times
- every X hours
- specific weekdays + time

Channel selection is hidden on the reminders page and uses reminder settings defaults.

Still open:
- surface occurrence actions (taken/skipped/snooze) in the reminders UI

Supporting web client/type changes:
- `apps/web/lib/api/core.ts`
- `apps/web/lib/api/reminder-client.ts`
- `apps/web/lib/types.ts`
- `apps/web/e2e/smoke.spec.ts`

Known issue:
- `pnpm web:typecheck` is currently blocked by unrelated missing exports used by `apps/web/app/alerts/page.tsx`

### Phase 6: Outcome tracking and companion integration

Status: `partially implemented`

Implemented:
- occurrence actions update occurrence state
- medication reminder actions create deterministic adherence events
- compatibility reminder metrics still compute through projected reminder events

Still open:
- companion snapshot should consume occurrence/action-level reminder outcomes directly
- dashboard and impact views should expose:
  - on-time vs late completion
  - snooze patterns
  - missed-dose trends
  - ignored reminder signals

## Validation Status

Passing:
- targeted reminder/backend Ruff checks
- targeted reminder and medication pytest suites:
  - `tests/infrastructure/test_structured_reminder_repository.py`
  - `tests/api/test_api_structured_reminders.py`
  - `tests/api/test_api_reminders.py`
  - `tests/api/test_api_medications.py`
  - `tests/infrastructure/test_reminder_scheduler.py`
  - `tests/application/test_reminder_notification_service.py`

Blocked by unrelated existing issue:
- `pnpm web:typecheck`
  - `apps/web/app/alerts/page.tsx` imports missing `getAlertTimeline` and `triggerAlert` from `@/lib/api/workflow-client`

## Next Work

1. Replace more of the compatibility `ReminderEvent` scheduling path with direct occurrence-based scheduler behavior.
2. Finish schedule generation support for every-X-hours, weekdays, bedtime, PRN, and temporary-course reminders.
3. Add direct API tests for manual reminder-definition create/update.
4. Add occurrence-state automation for grace-window expiry, missed classification, and retry limits.
5. Move medication intake confirmation onto the reminder-definition path explicitly.
6. Feed structured occurrence outcomes into companion snapshot, engagement, and impact modules.

## Future Phases

### Phase A: Workflow graphs

- Add `features/reminders/workflows/daily_generation_graph.py` only if reminder orchestration becomes genuinely multi-step.

### Phase B: Richer context-relative anchors

- Extend event-relative scheduling beyond meals to sleep, symptoms, exercise, and clinician checkpoints.
- Allow per-user anchor customization.

### Phase C: PRN and safety-aware guardrails

- Add per-reminder max daily usage, minimum spacing, and overuse warnings.

### Phase D: Escalation and proactive outreach

- Repeated high-risk misses can trigger companion follow-up, adherence summaries, or caregiver escalation.

### Phase E: Adaptive tuning

- Suggest reminder-time changes based on observed behavior while keeping user confirmation mandatory.

### Phase F: Expanded transport

- Extend adapters for email, SMS, Telegram, WhatsApp, and WeChat while preserving in-app parity.
