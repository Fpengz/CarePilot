# Reminders Page Clarity + Manual Create Design

## Goal
Make the reminders page understandable and actionable by default, add manual reminder creation with a minimal schedule set, and keep delivery logs available but de-emphasized.

## Scope
- UI hierarchy and copy fixes on the reminders page.
- Inline manual reminder creation with minimal schedule types.
- Planned reminders list as the primary view, with pause/activate controls.
- Upcoming/history as a collapsible section with per-occurrence delivery details.
- Update `reminder_service_plan.md` to reflect UI scope and progress.

Out of scope:
- New backend endpoints or schedule patterns beyond the minimal set.
- Meal-relative, PRN, or temporary-course manual creation.

## UX Structure
- **Create reminder (top)**: inline form with title, details, note, schedule type, and schedule inputs.
- **Planned reminders (primary list)**: reminder definitions with schedule summary and next trigger.
- **Upcoming & history (collapsed by default)**: occurrences and history; delivery logs per occurrence are a disclosure.
- **Copy**: user-facing labels, avoiding internal jargon.

## Scheduling Inputs (Minimal Set)
- One-time: date + time.
- Daily fixed times: multi-time input.
- Every X hours: interval hours.
- Specific weekdays: Monday-first weekday picker + time.
- Optional: start date, end date, timezone.
- Channels hidden; uses user settings (default in-app).

Weekday payloads use Monday-first indexing (1–7 for Mon–Sun).

## Data Flow
- Form submit: `POST /api/v1/reminders/definitions`.
- After submit: refresh definitions + upcoming/history.
- Planned reminders show next trigger computed from upcoming occurrences.
- Pause/activate: `PATCH /api/v1/reminders/definitions/{id}`.

## Risk Notes
- Manual schedule payloads must align with existing API contract.
- Avoid breaking existing occurrence actions and legacy projection list.

## Validation
- Manual UI testing of each schedule type.
- Smoke test updated to assert presence of the create panel.
