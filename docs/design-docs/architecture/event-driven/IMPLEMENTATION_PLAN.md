# Implementation Plan (Documentation Roadmap)

## Goal

Align documentation with current architecture, not a system rewrite.

## Phase 1 — Documentation Alignment

- Define the event model and timeline semantics
- Document agent contracts and result envelopes
- Clarify orchestration boundaries between workflows and features
- Note orchestration reality: chat, meals, and medications use LangGraph
  workflows under `src/care_pilot/features/**/workflows/*`
- Add refactor guardrail checklist (no agent side effects, no event bus,
  workflows orchestrate, services execute)

## Phase 2 — Observability

- Document tracing strategy
- Add timeline visibility guidance
- Improve event debugging references

## Phase 3 — Agent Expansion

- Formalize agent categories
- Standardize `AgentResult` usage across docs
- Document evaluation and safety gates

## Phase 4 — Event Coverage

- Expand domain event coverage
- Ensure all major flows emit events consistently
- Improve timeline completeness guidance

## Phase 5 — Future (Optional)

- Evaluate where checkpointing/interrupts add value and apply LangGraph
  persistence selectively
- Introduce more autonomous agents only where specialization improves outcomes
- Enhance proactive companion behavior

## Non-Goals

- No event bus introduction
- No rewrite of services
- No breaking API changes

## Refactor Guardrails (Checklist)

- Agents remain stateless and proposal-only
- No agent-to-agent calls or implicit loops
- All execution remains in features/services
- Orchestration stays in workflows and feature orchestrators
- Event timeline remains the source of traceability (no global bus)
