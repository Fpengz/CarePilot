# Core Beliefs (Agent-First CarePilot)

These beliefs define how we build CarePilot so that both humans and agents can reason about the system without relying on external context.

## 1. Repository Knowledge Is the System of Record
If it is not in this repository (code, docs, schemas, plans), it does not exist for agents. Every durable decision must land in `docs/` or in code.

## 2. AGENTS.md Is a Map, Not an Encyclopedia
`AGENTS.md` is intentionally short and points to indexed sources of truth. Long-form context belongs in `docs/` and must be indexed.

## 3. Progressive Disclosure Over Exhaustive Instructions
Start with a clear entry point, then link to deeper context. Avoid large, monolithic documents that dilute priority.

## 4. Deterministic First, Agents Second
Domain rules, persistence, and safety checks are deterministic. Agents are inference-only and must use typed contracts.

## 5. Architecture Boundaries Are Enforced
- `features/` owns product behavior.
- `agent/` owns inference logic.
- `platform/` owns infrastructure adapters.
- `core/` owns shared primitives.

## 6. Documentation Must Be Verifiable
Indexes track `Status`, `Last Verified`, and `Owner`. Stale docs are either refreshed or marked deprecated.

## 7. Plans Are First-Class Artifacts
Active, in-progress, and completed plans live under `docs/exec-plans/`. Major changes must leave a trace in plans or change logs.

## 8. Make History Legible
Use change logs and refactor history to preserve context across time. Avoid ephemeral notes as the sole record of decisions.
