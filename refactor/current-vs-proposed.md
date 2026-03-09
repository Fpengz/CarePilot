# Current vs Proposed

## Purpose

Clarify what the existing codebase already supports versus what the refactor package is proposing as extensions or net-new features.

This avoids two common mistakes:

- underselling the current codebase by pretending everything is greenfield
- overselling the hackathon plan by claiming features that are already present as if they were new inventions

## Current Codebase: Already Present

Based on the current architecture and feature audit, the repository already includes:

- meal analysis and weekly diet pattern analysis
- adaptive meal recommendation with persisted profile state
- medication tracking and adherence metrics
- reminder scheduling and delivery workflows
- symptom check-ins and summaries
- report parsing support
- numerical trend and delta analysis
- clinician-oriented clinical cards
- workflow replay and timeline traces
- RBAC and policy-protected routes
- emotion inference endpoints and runtime integration

Key references:

- `docs/feature-audit.md`
- `ARCHITECTURE.md`
- `docs/api-emotions-contract.md`
- `docs/emotion-integration.md`

## Current Codebase: Present but Not Yet Strong Enough for the Hackathon Answer

These capabilities exist in some form, but do not yet fully answer the hackathon story on their own:

- reminders exist, but not yet as a clearly articulated proactive engagement engine
- clinical cards exist, but not yet framed as a low-burden clinician copilot digest workflow
- metrics exist, but not yet organized as a pilot-ready impact measurement framework
- emotion inference exists, but not yet fully integrated into adaptive coaching and outreach decisions
- meal analysis exists, but the hackathon answer wants stronger Singapore-localized, culturally realistic positioning
- retrieval integration exists externally through the teammate-owned Chroma setup, but the codebase does not yet formalize it as a first-class evidence service boundary

## Proposed Extensions

These are the major proposed evolutions of existing capabilities:

### Proactive Engagement

Extend:

- reminders
- adherence tracking
- workflow scheduling
- emotion inference

Into:

- `Engagement Intelligence Service`
- relapse detection
- timing-aware nudges
- tone-aware outreach
- caregiver escalation thresholds

### Hyper-Personalization

Extend:

- current meal analysis
- report parsing
- trend computation
- profile state

Into:

- `Personalization Engine`
- multi-source context fusion
- culture/language/literacy-aware recommendation shaping
- patient-specific prioritization of what matters now

### Patient-Clinician Bridge

Extend:

- current clinical cards
- current trends
- current workflow traces

Into:

- `Clinician Copilot Summary Service`
- concise action-oriented digests
- ranked intervention suggestions
- low-burden escalation summaries

### Real-World Impact

Extend:

- existing metrics and trend endpoints
- adherence data
- reminder outcomes

Into:

- `Impact Measurement Service`
- baseline/follow-up comparisons
- patient/cohort dashboards
- clinician-efficiency proxies
- pilot KPI framework

## Net-New Features Proposed

These are the cleanest examples of genuinely new platform features in the refactor package:

- `Perception and Localization Service` as an explicit multimodal boundary
- `EvidenceRetrievalPort` over the integrated RAG backend
- `Engagement Intelligence Service`
- `Personalization Engine`
- `Clinician Copilot Summary Service`
- `Impact Measurement Service`

## Net-New Product Behaviors Proposed

These user-visible behaviors are proposed beyond the current baseline:

- proactive meal-risk streak nudges
- disengagement-sensitive tone adaptation
- caregiver notification only after explicit threshold crossing
- fused meal/report/emotion/profile guidance in one interaction
- clinician digest that highlights what changed and what to do next
- impact views that show whether the companion is helping

## Consolidated Interpretation

The refactor package should be interpreted as:

- `reuse what already works`
- `formalize what is currently implicit`
- `upgrade what already exists into a stronger hackathon answer`
- `add a small number of truly new modules where the current codebase is not sufficient`

## Source of Truth Rule

For implementation:

- use `master-plan.md` as the source of truth
- use this file to understand the delta from the current codebase
- use `hackathon-answer.md` to shape the deck, pitch, and demo narrative
