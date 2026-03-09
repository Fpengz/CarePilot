# Refactor Package

## Purpose

This folder contains the hackathon refactor package for evolving the system into an AI health companion with a policy-governed modular-monolith runtime.

This package is intended to support architecture review, scoping, and engineering planning.

The repository now already contains an implemented companion backbone under:
- `src/dietary_guardian/domain/care/`
- `src/dietary_guardian/application/case_snapshot/`
- `src/dietary_guardian/application/personalization/`
- `src/dietary_guardian/application/engagement/`
- `src/dietary_guardian/application/care_plans/`
- `src/dietary_guardian/application/clinician_digest/`
- `src/dietary_guardian/application/impact/`
- `src/dietary_guardian/application/interactions/`

Interpret the `refactor/` docs as architectural support for that direction, not as a competing source of truth over implemented code and top-level docs.

## Document Set

- `hackathon-answer.md`
  Judge-facing narrative that answers the four challenge questions through one product story, signature journeys, clinician workflow, and KPI framework.
- `master-plan.md`
  Consolidated implementation-ready refactor spec and the single source of truth for product/engineering scope, architecture, and rollout.
- `current-vs-proposed.md`
  Delta between the existing codebase and the proposed hackathon/system extensions: what already exists, what is being extended, and what is net new.
- `system-architecture.md`
  Supporting architecture elaboration for `master-plan.md`.
- `service-contracts.md`
  Supporting contract elaboration for `master-plan.md`.
- `safety-spec.md`
  Supporting safety appendix for `master-plan.md`.
- `data-model.md`
  Supporting data-model appendix for `master-plan.md`.
- `execution-plan.md`
  Supporting rollout appendix for `master-plan.md`.
- `tech-stack.md`
  Supporting stack appendix for `master-plan.md`.
- `pydanticai-patterns.md`
  Supporting agent-orchestration appendix for `master-plan.md`.

## Core Decisions

- Build a `capability-first platform`, not a collection of standalone specialist agents.
- Use `agents` only for narrow reasoning tasks that benefit from model specialization.
- Keep `policy and safety` outside prompts and enforce them as a first-class platform layer.
- Use `typed longitudinal state + event history` as the system of record, not chat memory.
- Treat `workflows` as durable products for chronic-care and prevention journeys.
- Make `evaluation and replay` mandatory platform capabilities.

## Design Status

This package is sufficient to start:

- architecture review
- boundary definition
- schema review
- engineering decomposition
- phased implementation planning

`master-plan.md` remains the primary source of truth inside `refactor/`, but the active repository-level source of truth is now:
- `README.md`
- `ARCHITECTURE.md`
- `SYSTEM_ROADMAP.md`
- implemented code under `src/dietary_guardian/domain/` and `src/dietary_guardian/application/`

This package is not yet a full production launch dossier. Before rollout, engineering still needs:

- final legal and compliance review
- region and data residency decisions
- SLO and capacity targets
- infrastructure cost envelope
- model vendor and routing decisions
- security threat model sign-off

## Recommended Reading Order

1. `hackathon-answer.md`
2. `master-plan.md`
3. `current-vs-proposed.md`
4. `system-architecture.md`
5. `data-model.md`
6. `service-contracts.md`
7. `safety-spec.md`
8. `tech-stack.md`
9. `pydanticai-patterns.md`
10. `execution-plan.md`
