---
title: Balanced UI Simplification
date: 2026-03-12
owners: ["codex"]
status: approved
---

# Balanced UI Simplification

## Goal
Apply a balanced simplification pass across all web pages: one dominant primary panel per page, one supporting rail/stack, and reduced nested borders to achieve a calmer, more trustworthy, premium interface.

## Scope
- All pages under `apps/web/app/**`.
- Shared layout patterns for panels, cards, and supporting rails.
- Chat page re-layout to a calm two-column workspace with a context rail.

Out of scope:
- Backend API changes.
- Route or navigation changes.
- Feature logic refactors.

## Design Decisions
- Primary panel: holds the main workflow and CTA.
- Supporting rail: holds secondary insights, history, or logs.
- Remove nested card stacks when they don’t add structural clarity.
- Use `soft-block` and `clinical-alert` for light grouping without borders.

## Page Mapping
- Dashboard: primary summary panel + secondary alerts/profile rail.
- Meals: primary analysis panel + history/suggestions rail.
- Metrics: primary trends panel + supporting details rail.
- Insights: primary generate/selected panel + history/safety rail.
- Reminders: primary actions panel + metrics/settings rail.
- Clinician digest: primary summary + evidence/changes rail.
- Chat: primary conversation, secondary context rail.

## Validation
- `pnpm web:lint`
- `pnpm web:typecheck`
- Manual review in light/dark mode.
