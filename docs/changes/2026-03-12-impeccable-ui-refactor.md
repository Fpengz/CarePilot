# Impeccable UI Refinement (2026-03-12)

## Summary
Refined the Clinical Calm UI to improve hierarchy clarity, reduce visual noise, and create a calmer premium feel across all pages.

## Global Design Adjustments
- Increased surface contrast and added `--border-soft` to reduce hard outlines.
- Softened card and panel borders; elevated shadows for a premium surface stack.
- Introduced utility classes for calm grouping (`soft-block`, `section-stack`).
- Expanded typography hierarchy for page titles and section headers.

## Component Updates
- Cards and navigation items now use softer borders and calmer surfaces.
- Dashboard “next guidance” blocks use soft surface panels instead of nested bordered cards.
- Data list rows use softer borders and larger padding for easier scanning.

## Validation
- `pnpm web:lint`
- `pnpm web:typecheck`
