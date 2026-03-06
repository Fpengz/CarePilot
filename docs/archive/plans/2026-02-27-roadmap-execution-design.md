> [!WARNING]
> Historical archive only. Content may be outdated.
> Canonical docs: `README.md`, `docs/roadmap-v1.md`, `docs/feature-audit.md`, `docs/config-reference.md`.

> Historical planning document.
> Active planning index: `docs/plans/README.md`.

# Roadmap Execution Design (Non-Interactive)

Date: 2026-02-27
Scope: Phases 1-5 in one uninterrupted implementation pass.

## Context and Constraints
- User requires non-interactive execution with no pause between phases.
- Preserve backward compatibility where possible.
- Reduce router glue and centralize error semantics.
- Strengthen observability across API/application/workflow layers.

## Approaches Considered
1. Incremental endpoint-only edits per phase.
- Pros: low blast radius.
- Cons: duplicated patterns remain; weak consistency.

2. Shared platform primitives first (error + observability), then endpoint/UI hardening. (Chosen)
- Pros: consistent semantics across routes, simpler regression protection.
- Cons: larger cross-cutting patch.

3. Full domain rewrite for strict layered architecture.
- Pros: ideal structure.
- Cons: high risk for roadmap timeline, compatibility risk.

## Chosen Design
- Add centralized API error abstraction and global exception handlers.
- Move remaining suggestions orchestration out of router into application-facing service.
- Add request context helpers and standardized structured log events.
- Propagate request/correlation IDs into workflow generation paths not currently wired.
- Introduce typed suggestions view models in web app and explicit UI state rendering for loading/empty/error/partial.
- Harden household-based suggestion access through centralized access policy checks and targeted edge-case tests.
- Complete meal pagination semantics via cursor contract while preserving existing limit behavior.
- Add CI workflow, container hardening, and app lifecycle close hooks.

## Testing Strategy
- TDD per change cluster:
  - Add/extend API tests first for expected failures and new contracts.
  - Implement minimal changes to pass.
  - Refactor safely while keeping tests green.
- Run focused test slices after each phase and final backend/full-stack validation.

## Risk Management
- Preserve legacy `detail` field in error responses while adding structured `error` payload.
- Keep existing query parameters and response fields; add new optional fields for forward compatibility.
- Add regression tests for suggestions, households, observability headers/log schema, and meal pagination.
