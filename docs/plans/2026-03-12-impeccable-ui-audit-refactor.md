---
title: Impeccable UI Audit and Refinement
date: 2026-03-12
owners: ["codex"]
status: approved
---

# Impeccable UI Audit and Refinement

## Goal
Refine the existing Clinical Calm UI to be calmer, more trustworthy, more premium, and less generic SaaS by improving hierarchy, spacing rhythm, CTA clarity, and surface hierarchy across all pages.

## Scope
- All web routes under `apps/web/app/**`.
- Shared layout components (`AppShell`, sidebar, top bar, page titles).
- Global tokens and base UI components (cards, buttons, typography).

Out of scope:
- Backend API or data flow changes.
- New routes or navigation items.
- Feature logic refactors.

## Audit Summary
- Hierarchy: too many equal-weight cards reduce scannability.
- Spacing: uniform padding flattens emphasis.
- Typography: title/body sizes too close in several views.
- Surfaces: nested borders add visual noise.
- CTA: primary actions compete with secondary controls.

## Design Decisions
- Increase hierarchy with larger titles and smaller section labels.
- Introduce asymmetrical spacing rhythm: tight clusters + airy separations.
- Reduce nested borders; use surface contrast to separate layers.
- Use a single primary CTA per page, placed consistently.
- Standardize calm surface stack: background → panel → surface → soft block.

## Implementation Plan
1. Adjust global tokens to increase contrast between background, panel, and surface.
2. Update base card and button styles for softer, premium surfaces.
3. Add new utility classes for soft blocks and section spacing.
4. Refactor core pages to reduce nested containers and improve grouping.
5. Update timeline/list patterns to reduce visual noise.

## Validation
- `pnpm web:lint`
- `pnpm web:typecheck`
- Manual review in light/dark mode.

## Risks
- Over-reducing borders can reduce perceived structure if surface contrast is insufficient.
- CTA consolidation must not hide secondary workflows.
