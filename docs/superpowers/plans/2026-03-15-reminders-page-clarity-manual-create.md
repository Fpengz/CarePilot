# Reminders Page Clarity + Manual Create Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the reminders page to be clear and usable by default, add manual reminder creation for minimal schedule types, and update reminder plan documentation.

**Architecture:** Keep reminder creation and listing on the web page; use existing reminder definition APIs for create and patch. Upcoming/history data stays unchanged and is presented in a collapsed view with delivery logs disclosed per occurrence.

**Tech Stack:** Next.js, React, TypeScript, existing web API client in `apps/web/lib/api`.

---

## Chunk 1: Plan Updates and API Client Contracts

### Task 1: Add reminder definition create/patch API helpers and types

**Files:**
- Modify: `apps/web/lib/types.ts`
- Modify: `apps/web/lib/api/core.ts`
- Modify: `apps/web/lib/api/reminder-client.ts`

- [ ] **Step 1: Write the failing type usage in the page (temporary)**

Use a stub type reference so TypeScript reveals the missing types in the next step.

- [ ] **Step 2: Add request/response types**

Add `ReminderDefinitionCreateRequest`, `ReminderDefinitionPatchRequest`, and `ReminderDefinitionEnvelopeResponse` in `apps/web/lib/types.ts` mirroring backend schemas.

- [ ] **Step 3: Add API functions**

Implement:
`createReminderDefinition(payload)` and
`patchReminderDefinition(definitionId, payload)` in `apps/web/lib/api/core.ts`.

- [ ] **Step 4: Re-export from reminder client**

Expose new API helpers from `apps/web/lib/api/reminder-client.ts`.

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/types.ts apps/web/lib/api/core.ts apps/web/lib/api/reminder-client.ts
git commit -m "feat(web): add reminder definition create/patch client"
```

## Chunk 2: Reminders Page Layout and Manual Create

### Task 2: Add manual creation panel and restructure lists

**Files:**
- Modify: `apps/web/app/reminders/page.tsx`

- [ ] **Step 1: Add form state and helpers**

Add state for title, details, note, schedule type, schedule inputs, start/end date, timezone, and submission status.

- [ ] **Step 2: Build schedule payload builder**

Implement a function that maps the minimal schedule types to the `ReminderScheduleRuleApi` payload.

- [ ] **Step 3: Implement create handler**

Submit to `POST /api/v1/reminders/definitions`, then refresh definitions/upcoming/history.

- [ ] **Step 4: Update page hierarchy and copy**

Move the create panel to the top, make “Planned reminders” the primary list, and place “Upcoming & history” in a collapsible section. Update copy to user-facing labels.

- [ ] **Step 5: Add planned reminder pause/activate**

Add a toggle that calls `PATCH /api/v1/reminders/definitions/{id}` to pause/activate.

- [ ] **Step 6: Add per-occurrence delivery disclosure**

Move delivery logs into a disclosure within the selected occurrence context.

- [ ] **Step 7: Commit**

```bash
git add apps/web/app/reminders/page.tsx
git commit -m "feat(web): refresh reminders UI and add manual creation"
```

## Chunk 3: Tests and Docs

### Task 3: Update smoke test and plan doc

**Files:**
- Modify: `apps/web/e2e/smoke.spec.ts`
- Modify: `reminder_service_plan.md`

- [ ] **Step 1: Update smoke test**

Assert the “Create reminder” panel exists.

- [ ] **Step 2: Update reminder_service_plan**

Mark manual creation UI implemented, list schedule types supported, and note the new page hierarchy.

- [ ] **Step 3: Commit**

```bash
git add apps/web/e2e/smoke.spec.ts reminder_service_plan.md
git commit -m "docs(web): update reminders plan and smoke coverage"
```

## Validation

- Frontend manual checks:
1. Create one reminder for each schedule type and verify it appears in Planned reminders.
2. Generate today’s reminders and confirm upcoming/history show occurrences.
3. Verify occurrence actions still work.

- Optional automated checks (if running web tests):
`pnpm web:lint`
`pnpm web:typecheck`
`pnpm web:build`

## Risk

- Payload mismatch with backend reminder schedule schema.
- Regression in occurrence selection and delivery log display after layout changes.
