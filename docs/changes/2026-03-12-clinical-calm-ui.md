# Clinical Calm UI Refresh (2026-03-12)

## Summary
Replaced the web UI styling and layouts with a Clinical Calm design system across the core patient companion pages, emphasizing calm hierarchy, card-based structure, and consistent light/dark themes.

## Updated Global System
- Reworked design tokens in `apps/web/app/globals.css` for clinical neutrals and soft medical blue accent.
- Added Clinical Calm utility classes (`clinical-card`, `clinical-panel`, `clinical-kicker`, `clinical-alert`, etc.).
- Refined base card and button components for softer shadows and calmer surfaces.

## Page-Level Updates
- **Dashboard**: new clinical summary panel, primary metrics grid, and AI alert cards.
- **Meals**: reorganized tab labels, improved meal analysis layout, and introduced image preview.
- **Meal History**: switched to timeline-style entries for readability.
- **Daily Nutrition** (`/metrics`): clarified labels and tuned copy.
- **Insights** (`/suggestions`): replaced “workflow” framing with clinical recommendations layout.
- **Reminders**: updated page framing for adherence tracking.
- **Clinician Digest**: upgraded summary cards and evidence panels to clinical alert styling.

## Validation
- `pnpm web:lint`
- `pnpm web:typecheck`
