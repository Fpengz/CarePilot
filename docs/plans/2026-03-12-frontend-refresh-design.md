# Frontend Refresh Design (2026-03-12)

## Summary
Update the Next.js app router and UI to match the new SSE envelope, then refresh the global shell and all top-level routes using a clinical editorial design system. The goal is a calm, data-forward interface with distinctive typography, subtle motion, and consistent page scaffolding.

## Visual Direction
- Clinical editorial: clear hierarchy, refined typography, muted inks, and calm contrast.
- Warm neutrals with a restrained teal accent.
- Fewer cards, more structured surfaces and context rails.

## UI Architecture
- AppShell drives a consistent page scaffold (header, main, rail pattern).
- PageTitle is the common entry for hero context and actions.
- Sidebar + topbar emphasize clarity over density.

## Router/SSE
- Chat and audio pages parse `{ event, data }` SSE envelopes.
- Backend proxy preserves `text/event-stream` behavior and avoids buffering.

## Scope
- Global shell, sidebar, topbar, mobile nav, and shared typography/color system.
- Full page layout refresh across all top-level routes.
