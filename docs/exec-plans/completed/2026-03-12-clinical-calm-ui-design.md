---
title: Clinical Calm UI Redesign
date: 2026-03-12
owners: ["codex"]
status: approved
---

# Clinical Calm UI Redesign

## Goal
Replace the existing web UI with a calm, clinical, card-based interface that prioritizes readability, trust, and clear hierarchy for a patient companion platform.

## Scope
- Update global design system tokens (color, typography, spacing).
- Replace layouts and components in all existing web routes with Clinical Calm patterns.
- Provide consistent light + dark themes.
- Maintain existing routing and data wiring (no backend behavior changes).

Out of scope:
- Backend API changes.
- New routes or navigation structure changes.
- Feature logic refactors.

## Design Principles
- Calm, clinical, high-trust visuals.
- Minimal noise, strong hierarchy.
- Neutral palette with one soft medical blue accent.
- Generous whitespace and 8px spacing rhythm.
- Subtle shadows and rounded corners (8–12px).
- Card-based grouping for content.
- AI insights presented as professional assistant cards, not chat UI.

## Layout System
- Left sidebar navigation with clear active state.
- Top bar for context and key actions.
- Main content area composed of modular cards.
- Right rail only when needed; otherwise single-column focus for readability.

## Component Patterns
- Primary cards: daily summary, key metrics, AI alerts.
- Supporting cards: hydration, trends, meal summaries.
- Logs: timeline lists for meals, reminders, activity.
- Charts: minimal line charts, progress bars, radial indicators, clean legends.
- Buttons: restrained accent for primary actions; outline for secondary.

## Light + Dark Themes
Both themes share identical structure and hierarchy. Dark mode uses soft charcoal surfaces with muted borders and the same accent hue.

## Pages Covered
1. Dashboard
2. Meal analysis results
3. Daily nutrition overview
4. Health insights / recommendations
5. Meal history timeline
6. Reminders & adherence tracking
7. Clinician summary view

## Validation
- `pnpm web:lint`
- `pnpm web:typecheck`
- Manual review in browser for visual consistency (light/dark).

## Risks
- Over-editing layout can reduce consistency if not applied across all routes.
- Incomplete token updates can create mismatched visuals in dark mode.
*** End Patch  大发快三官网 to=functions.apply_patch to=commentary  天天中json to=functions.apply_patch code){
