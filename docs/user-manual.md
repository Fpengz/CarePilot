# User Manual

Last updated: 2026-03-06  
Audience: end users and technical operators/contributors

## System Capabilities
- Health profile setup and guided onboarding.
- Meal logging and daily/weekly nutrition summaries.
- Recommendation generation and substitution guidance.
- Medication regimen tracking and adherence logging.
- Reminder generation and notification delivery.
- Symptom check-ins and report context synthesis.
- Clinical card generation and trend surfaces.
- Workflow trace inspection and governance tools (admin scopes).

## Track A: End User Guide

### 1) Account and Profile Setup
1. Sign up or log in from `/signup` or `/login`.
2. Open `/settings`.
3. Complete guided health-profile onboarding.
4. Save profile updates and verify completion status.

### 2) Log Meals and View Nutrition Progress
1. Open `/meals`.
2. Log a meal entry.
3. Review daily consumed vs remaining targets.
4. Review weekly summary and pattern flags.

### 3) Manage Medication and Reminders
1. Open `/medications` and create regimen entries.
2. Record adherence events (taken/missed/skipped).
3. Open `/reminders` and generate reminders.
4. Confirm reminders and review status history.

### 4) Record Symptoms and Parse Reports
1. Open `/symptoms` and submit check-ins.
2. Open `/reports` and parse pasted report text.
3. Review symptom summary context and extracted readings.

### 5) Generate Clinical Cards and View Metrics
1. Open `/clinical-cards` to generate/list cards.
2. Open `/metrics` to inspect trend and delta outputs.

## Track B: Operator/Contributor Usage

### 1) Demo Accounts
Use built-in local demo credentials:
- `member@example.com` / `member-pass`
- `helper@example.com` / `helper-pass`
- `admin@example.com` / `admin-pass`

### 2) Admin Workflow Inspection
1. Log in as admin.
2. Open `/workflows`.
3. List workflows, fetch a correlation trace, and inspect timeline events.
4. Load runtime contract and snapshot views.
5. Inspect/create/evaluate tool policies as needed.

### 3) Household Care Monitoring
1. Open `/household`.
2. Use care member views for read-only monitoring of profile/meal/reminder context.

## Example End-to-End Workflows

### Workflow: Meal to Recommendation Loop
1. Log a meal in `/meals`.
2. Generate recommendation/suggestion.
3. Record interaction feedback.
4. Review updated guidance and daily summary hints.

### Workflow: Medication Adherence Lifecycle
1. Add a regimen in `/medications`.
2. Generate reminders in `/reminders`.
3. Confirm reminders and/or log adherence events.
4. Review adherence metrics and history.

### Workflow: Symptom to Report Context
1. Create symptom check-ins in `/symptoms`.
2. Parse report text in `/reports`.
3. Validate symptom summary appears in parsed report context.

### Workflow: Governance Inspection (Admin)
1. Open `/workflows`.
2. Load runtime contract and snapshots.
3. Compare snapshot versions.
4. Evaluate tool policy decision for role/agent/tool/environment.

## Troubleshooting for Users
- If pages fail to load data, re-authenticate and refresh session.
- If reminders are not arriving, verify notification preferences/endpoints.
- If features appear missing, confirm user role and scope permissions.

## When to Update This Document
- New user-visible capabilities/routes.
- Changes to key task flows.
- Changes to admin/operator workflows.
