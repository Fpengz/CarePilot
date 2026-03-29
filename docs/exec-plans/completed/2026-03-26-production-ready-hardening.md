# Implementation Plan: Production-Ready Hardening (2026-03-26)

## Context
Transition from a "hackathon prototype" to a "production-ready" system by addressing architectural debt, performance bottlenecks, and reliability gaps identified during the codebase audit.

## High-Priority Tasks

### 1. Multi-Agent & Chat Performance
- [ ] **Implement Fast-Path Intent Gate**: Add a lightweight classifier in `ChatOrchestrator` to bypass LangGraph for social/low-intent queries.
- [ ] **Implement Context Pruning**: Add relevance-based filtering to `PatientCaseSnapshot` generation to reduce token usage and improve reasoning focus.
- [ ] **Consolidate ChatAgent**: Remove legacy handler leftovers and finalize the `ChatOrchestrator` core refactor.
- [ ] **Centralize EmotionAgent**: Unify emotion inference in a single runtime with explicit feature-flag control.

### 2. Infrastructure Reliability
- [ ] **Protocol Migration**: Replace all remaining `getattr`-based repository magic (especially in `alert_outbox.py`) with strict Python Protocols.
- [ ] **Transactional Timeline Writes**: Design and implement an outbox-backed persistence path for event logs to ensure transactional integrity.
- [ ] **Feature Flags**: Migrate ad-hoc environment checks (`if env == "dev"`) to structured `FeatureFlags` in `AppSettings`.

### 3. Submission & Documentation
- [ ] **Prompt Catalog**: Extract and document all system prompts in `docs/prompt_catalog.md`.
- [ ] **Technical Overview**: Draft the Product + Technical summary for the hackathon submission.

## Validation Strategy
1. **Performance**: Measure latency reduction for "social" queries after Fast-Path implementation.
2. **Stability**: Ensure `web-e2e` tests pass after refactoring repository protocols.
3. **Audit**: Verify no `getattr` calls remain in critical outbox or persistence paths.
4. **Type Safety**: Run `uv run ty check .` to verify type consistency with the new Protocols.
