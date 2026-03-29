# Chat Agent UI Redesign Design

Date: 2026-03-13

## Goal
Deliver a production-grade Chat Agent page for the AI Health Companion that feels clinical but warm, trustworthy, calm, and information-rich without clutter. Preserve all existing behaviors (SSE streaming replies, audio recording, meal proposal confirmation) while adding structured message presentation and a premium, explainable layout.

## Constraints
- No removal of existing behaviors or flows.
- Web UX lives in `apps/web/**`.
- Avoid generic chatbot layout patterns and “AI SaaS” aesthetic.
- Use distinct typography (no Inter/Roboto/system defaults).

## Architecture
Single page layout with three regions:
1. **Left rail** for health signals, focus, and next check-in.
2. **Main conversation stream** with structured message cards by type.
3. **Bottom input dock** with suggestion chips, message input, send, and microphone.

Structured message rendering is purely frontend: infer message type from existing message attributes and content hints; do not change backend payloads.

## Visual Direction
- **Tone:** Editorial clinical. Calm neutrals, warm tints, restrained rounding, subtle elevation.
- **Typography:** Distinct display + readable body font pairing using `next/font/google` with a clear scale.
- **Hierarchy:** Title/summary sections, message type badges, confidence indicator, reasoning disclosure.
- **Surfaces:** Lightly raised panels, minimal borders, no nested card stacks.

## Components
- `ChatRail`: left rail signals and next steps.
- `MessageCard`: user/assistant message with structured slots.
  - Optional: title, explanation, confidence meter, reasoning block.
  - Supports message kinds: proactive alert, meal analysis, recommendation, follow-up clarification, trend insight.
- `ChatInput`: suggestion chips + input + send + mic.
- Internal subcomponents: `MessageKindBadge`, `ConfidenceMeter`.

## Data Flow
- Preserve existing streaming event ingestion and audio recording.
- Add a client-side mapper to derive `MessageKind` and metadata from existing content:
  - `proactive_alert` for warning/error tags.
  - `meal_analysis` when meal analysis cues exist.
  - `trend_insight` for longitudinal or trend cues.
  - `recommendation` for action-oriented outputs.
  - `follow_up` for clarification prompts.
  - default to `plain`.

## Error Handling
- No new modal flows.
- Inline non-blocking notices for stream interruption and audio errors.

## Accessibility
- Ensure keyboard navigation for chips and input.
- Use sufficient contrast on badges and text.
- Maintain readable line lengths and spacing.

## Validation
- `pnpm web:lint`
- `pnpm web:typecheck`
- `pnpm web:build`

## Risks
- Over-styling could harm readability; mitigate with restrained palette and spacing.
- Heuristic message typing may misclassify; allow fallback to `plain` without breaking layout.
