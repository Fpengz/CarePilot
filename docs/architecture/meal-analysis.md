# Meal Analysis Agents

## Purpose

This document explains the target meal‑analysis architecture for Dietary Guardian, what is already implemented, and the highest‑value next improvements for the meal‑analysis stack.

The system is organized around a deliberate split:

- Perception first
- Canonical food retrieval and search second
- Deterministic reconciliation and enrichment third
- User confirmation and correction where needed
- Persistence and downstream care logic after finalization

That split keeps image understanding bounded, keeps nutrition and risk logic auditable, gives users a correction path when confidence is weak, and ensures downstream companion surfaces consume a stable enriched meal event rather than raw model guesses.

## Diagram Reference

The visual target architecture lives in `docs/architecture/meal-analysis-architecture.drawio`. It represents the intended end‑state. This document annotates the diagram with current implementation notes and highlights gaps explicitly.

## Design Principles

### Principle 1: Perception is not nutrition

The image‑capable model should answer only questions that require looking at the image:

- What foods are likely present
- What visible components are present
- Rough portion units and counts
- Visible preparation cues
- Image quality concerns
- Confidence and ambiguity

It should not be the source of truth for:

- Canonical food naming
- Nutrition totals
- Glycemic labels
- Risk tags
- Patient guidance
- Clinician‑facing conclusions

### Principle 2: Canonical food search owns candidate retrieval

After perception, the backend should search the canonical food store using deterministic retrieval and ranking signals:

- Perceived labels
- Candidate aliases
- Visible components
- Preparation cues
- Token overlap
- Future semantic retrieval support

The goal of this stage is not yet to finalize nutrition, but to produce strong canonical candidates for reconciliation.

### Principle 3: Deterministic reconciliation owns food facts

After candidate retrieval, the backend should:

- Reconcile perception evidence with canonical food candidates
- Choose the best canonical match when confidence is sufficient
- Preserve ambiguous or unresolved cases explicitly
- Estimate grams from portion references
- Attach deterministic nutrition and glycemic metadata
- Derive heuristic risk tags
- Produce a candidate enriched meal event

This stage owns auditable meal normalization.

### Principle 4: User confirmation is a correction layer, not the primary reasoning layer

User feedback should refine and finalize uncertain outcomes, not replace deterministic normalization.

The confirmation layer should support:

- Yes: accept the candidate meal event
- No: reject and edit the selected food or meal name
- Edit: adjust portions, components, or item composition
- Correction capture: feed mismatches back into curation and review workflows

The system should not ask for confirmation when confidence is high and evidence is clean.

### Principle 5: Guidance should consume finalized enriched meal events

Recommendation, case snapshot, trends, summaries, and clinician‑facing logic should work from finalized normalized meal data rather than raw perception output.

## Planned End‑to‑End Pipeline (Target)

```text
User Input (image or text)
  -> HawkerVision perception
  -> MealPerception (typed, bounded JSON)
  -> canonical food search
  -> deterministic reconciliation and enrichment
  -> CandidateMealEvent
  -> confidence gate
  -> user confirmation or correction when needed
  -> Final EnrichedMealEvent
  -> persistence
  -> downstream summaries, recommendations, trends, and clinician context
```

## Current End‑to‑End Pipeline (Implemented)

```text
User Input (image + optional meal_text)
  -> HawkerVision perception
  -> MealPerception
  -> canonical food ranking + deterministic normalization
  -> claim reconciliation (optional) + re‑normalization
  -> ValidatedMealEvent + NutritionRiskProfile
  -> persistence (observation + validated event + nutrition profile)
  -> workflow handoffs + downstream consumers
```

## Diagram Alignment (T1–T5)

| Tier | Diagram Nodes | Current Implementation | Notes |
| --- | --- | --- | --- |
| T1 Ingestion | Meal Image, User Text, Location + Context | `apps/api/carepilot_api/routers/meals.py` + `src/care_pilot/features/meals/api_service.py` | Location/context is limited to a lightweight session snapshot; no dedicated context ingestion service. |
| T2 Perception | Vision Agent, Dietary Agent, Context Ingestion Service | Vision: `src/care_pilot/agent/meal_analysis/vision_module.py` | Dietary Agent runs only as a handoff target; no in‑workflow dietary agent execution node. |
| T3 Reconciliation & Scoring | Reconciliation & Canonicalization, Nutrition & Risk Scoring | `src/care_pilot/features/meals/use_cases.py` + `src/care_pilot/features/meals/workflows/meal_upload_graph.py` | Canonical search and normalization are deterministic; risk tags are heuristic. |
| T4 Memory Stores | Meal Event Store, Nutrition Store, User Memory Store | Meal events and nutrition profiles persisted via `stores.meals.*` in the workflow | No user memory store writes in the current meal analysis flow. |
| T5 Intelligence & Action | Health‑State Interpretation, Recommendation Engine, Patient Response | Downstream consumers exist, but not part of the meal analysis workflow graph | These are system‑level consumers rather than direct steps in the meal analysis workflow. |

## Current vs Planned Gaps

| Capability | Planned | Current | Gap |
| --- | --- | --- | --- |
| CandidateMealEvent | Explicit candidate event before confirmation | No separate candidate event | Needs a distinct candidate model and persistence step. |
| Confirmation gate | Confidence‑gated confirmation loop | No confirmation loop | Workflow persists directly; manual review only flagged. |
| Dietary agent execution | Dedicated dietary agent stage | Handoff only | Add a dietary agent node or service call. |
| Context ingestion service | Explicit location/context ingestion | Lightweight session snapshot | Add context ingestion pipeline and contracts. |
| User memory store | Meal analysis writes to memory store | Not written | Add storage integration and downstream feedback loop. |

## Confidence‑Gated Interaction Model

High‑confidence flow

- Auto‑accept the candidate meal event
- Persist the finalized enriched meal event directly
- Optionally allow passive edit afterward

Medium‑confidence flow

- Show the top candidate
- Surface alternatives when useful
- Ask the user to confirm or correct

Low‑confidence flow

- Request explicit user correction
- Mark for manual review where appropriate
- Avoid silently inventing nutrition

This keeps UX fast when confidence is high and safe when confidence is weak.

## Module Map

Vision and perception

- `src/care_pilot/agent/meal_analysis/vision_module.py`

Domain contracts

- `src/care_pilot/features/meals/domain/models.py`

Application normalization, reconciliation, and enrichment

- `src/care_pilot/features/meals/use_cases.py`

Workflow orchestration

- `src/care_pilot/features/meals/workflows/meal_upload_graph.py`
- `src/care_pilot/features/meals/workflows/meal_upload_state.py`

Provider/runtime integration

- `src/care_pilot/agent/runtime/llm_factory.py`
- `src/care_pilot/agent/runtime/inference_engine.py`

Canonical food search, ranking, and loading logic

- `src/care_pilot/features/recommendations/domain/canonical_food_matching.py`
- `src/care_pilot/platform/persistence/food/ingestion.py`

Persistence

- `src/care_pilot/platform/persistence/sqlite_repository.py`

Compatibility helpers for downstream consumers

- `src/care_pilot/features/meals/presenter.py`

Example downstream consumers

- `src/care_pilot/features/meals/api_service.py`
- `src/care_pilot/features/recommendations/recommendation_service.py`
- `src/care_pilot/features/companion/core/companion_core_service.py`

Future feedback and review workflows

- Unresolved‑food review queue
- User correction store
- Canonical‑food curation workflow

## Core Contracts

### MealPerception

MealPerception is the bounded output of the perception layer.

It includes:

- meal_detected
- items
- uncertainties
- image_quality
- confidence_score

Each perceived item is represented by PerceivedMealItem:

- label
- candidate_aliases
- detected_components
- portion_estimate
- preparation
- confidence

This keeps the vision layer constrained to image understanding while still giving search and reconciliation enough evidence to disambiguate dishes.

### CandidateMealEvent

CandidateMealEvent is the deterministic output produced after canonical search and reconciliation, before final confirmation.

It should include:

- Proposed meal name
- Normalized items
- Nutrition estimate from canonical records
- Risk tags
- Unresolved items
- Source records
- Match confidence
- Review flags
- Explanation metadata

This is the candidate the system may auto‑accept or present to the user for correction.

### EnrichedMealEvent

EnrichedMealEvent is the finalized deterministic normalized output used across the rest of the system.

It includes:

- meal_name
- normalized_items
- total_nutrition
- risk_tags
- unresolved_items
- source_records
- needs_manual_review
- summary
- confirmation_status
- user_corrections where applicable

Each NormalizedMealItem captures:

- detected label
- canonical food match
- matched alias
- match strategy
- match confidence
- preparation
- portion estimate
- estimated grams
- deterministic item nutrition
- risk tags
- source dataset

## What the Vision Agent Should Do

HawkerVisionModule should use a perception‑only system prompt. The prompt should explicitly instruct the model to:

- Return strict MealPerception
- Detect likely foods and visible components
- Estimate coarse portions
- Describe preparation cues
- Report confidence and uncertainty
- Avoid generating nutrition, glycemic claims, risk tags, or advice

Important behavior

- Low‑confidence or ambiguous captures should return clarification‑style perception responses
- Test‑provider flows should emit deterministic MealPerception payloads for stable tests
- Image‑quality issues should be surfaced explicitly
- The perception layer should remain bounded even if future models become more capable

## What the Canonical Search Layer Should Do

The canonical search layer should:

- Search canonical food records using perceived labels and aliases
- Incorporate detected components and preparation cues
- Rank dish candidates deterministically
- Support future semantic retrieval without changing downstream contracts
- Return top candidates and match evidence for reconciliation

Current ranking signals

- Exact and partial alias matches weighted highest
- Detected component overlap adjusting score
- Preparation compatibility adjusting score
- Token overlap used as a weak tie‑breaker

Later improvements may include:

- Alias priority metadata
- Alias type metadata
- Cuisine‑aware tie‑breaking
- Dish‑family and variant modeling
- Semantic vector retrieval for fuzzy recall

## What the Deterministic Reconciliation Layer Should Do

The feature layer in `features/meals/use_cases.py` should handle:

- Legacy‑to‑perception conversion when needed
- Candidate reconciliation against canonical search results
- Portion‑unit to gram estimation
- Deterministic nutrition scaling from canonical records
- Heuristic risk‑tag derivation
- Component‑mismatch detection
- Meal‑level nutrition summation
- Unresolved‑item handling
- CandidateMealEvent construction
- EnrichedMealEvent finalization
- Compatibility MealState rebuilding where still required
- MealRecognitionRecord construction

Current normalization behavior

- Collect the observed label, candidate aliases, detected components, and preparation cue
- Retrieve and rank canonical food candidates
- Pick the best candidate when it clears the match threshold
- Estimate grams using stored portion references, default portion grams, or fallback unit heuristics
- Scale nutrition from the matched canonical record
- Derive heuristic risk tags
- Add component_mismatch when visible evidence conflicts with the canonical record
- Keep the item unresolved when no safe canonical match exists

## User Confirmation and Correction Layer

Purpose

The user confirmation layer exists to finalize uncertain cases safely and to improve the system over time.

Supported actions

- Confirm the candidate meal event
- Reject the proposed dish and select another
- Edit portion estimates
- Add or remove meal items
- Flag unclear images or incorrect detections

Confirmation policy

- Auto‑accept when confidence is high and no review flags are present
- Request confirmation when match confidence is moderate
- Require correction when evidence is weak or unresolved

Feedback capture

Corrections should be stored for:

- Unresolved‑food curation
- Alias expansion
- Ranking improvement
- Future evaluation datasets
- Review‑queue prioritization

## Current Manual‑Review Rules

Normalization should mark a meal for manual review when any of the following is true:

- The vision layer already requested manual review
- One or more items are unresolved
- Any matched item has low match confidence
- Component or preparation evidence conflicts with the chosen canonical food
- Image quality is poor
- Image quality is only fair and perception confidence is also low
- User correction conflicts strongly with the top canonical match

That behavior is intentional. The system should surface uncertainty rather than silently force a confident nutrition result from weak evidence.

## Canonical Food Layer

The canonical food layer stabilizes meal naming, nutrition logic, glycemic metadata, and food provenance across perception and recommendation flows.

Current canonical model

CanonicalFoodRecord currently supports:

- food_id
- title
- aliases
- aliases_normalized
- slot
- venue_type
- cuisine_tags
- ingredient_tags
- preparation_tags
- nutrition
- health_tags
- risk_tags
- glycemic_index_label
- glycemic_index_value
- disease_advice
- alternatives
- serving_size
- default_portion_grams
- portion_references
- source_dataset
- source_type

Current data sources

The active canonical food layer is assembled from:

- DEFAULT_MEAL_CATALOG
- Singapore‑local seed data in `src/care_pilot/data/food/sg_hawker_food.json`
- Optional reduced USDA data in `src/care_pilot/data/food/usda_foods.json`
- Optional reduced Open Food Facts data in `src/care_pilot/data/food/open_food_facts_products.json`

Current ingestion posture

The code is wired for curated reduced source files rather than raw source mirrors. That is the right trade‑off for the current hackathon branch:

- Easier to reason about
- Easier to validate
- Easier to keep deterministic
- Compatible with future import and review workflows

## Persistence Model

Meal persistence should store more than the legacy meal state.

Meal record fields

MealRecognitionRecord should support:

- meal_state
- meal_perception
- candidate_enriched_event
- enriched_event
- confirmation_status
- user_corrections

Database support

SQLite support should include:

- Richer meal‑record JSON storage
- Canonical food persistence
- Food aliases
- Portion references
- Confirmation and correction records

This gives the system a path toward:

- Consistent meal history
- Repeatable analytics
- Auditable perception‑versus‑search‑versus‑reconciliation comparisons
- Clinician‑facing evidence later without reworking the storage model

## Downstream Consumer Strategy

The system should use helper utilities to let downstream services prefer finalized enriched data while still supporting legacy records where necessary.

Utility accessors

Current helper functions include:

- meal_display_name()
- meal_nutrition()
- meal_ingredients()
- meal_nutrition_profile()
- meal_confidence()
- meal_identification_method()
- meal_risk_tags()

Downstream adoption target

These consumers should prefer finalized enriched meal events:

- Daily nutrition summary
- Weekly nutrition summary
- Metric trend generation
- Case snapshot assembly
- Recommendation generation
- Recommendation‑agent temporal and substitution flows

They should not rely directly on raw perception output except for audit or evaluation views.

## Current Progress

Completed

- Perception‑first meal domain contracts were added
- HawkerVisionModule was refactored to emit bounded perception instead of model‑generated nutrition or advice
- Deterministic normalization and enrichment use cases were added
- Canonical food records now support aliases, portion references, default portions, glycemic metadata, and risk tags
- The canonical food layer now merges default meal‑catalog seeds, Singapore hawker data, and optional reduced external datasets
- Meal normalization now uses ranked candidate selection instead of label‑only lookup
- Component and preparation evidence now influence canonical dish selection
- Component and preparation mismatches now escalate meals to manual review
- SQLite persistence was extended for perception and enriched‑event storage
- Compatibility helpers were added for downstream services
- Downstream consumers were updated to prefer enriched meal events
- Targeted tests were added and updated for hawker‑vision perception flow, canonical food ranking behavior, meal normalization and manual‑review triggers, ingestion reducers, persistence round‑trip, and enriched‑event consumer behavior

Partially complete

- Compatibility still relies on rebuilding legacy MealState
- Risk‑tag derivation is deterministic but still heuristic rather than clinically calibrated
- Canonical matching is stronger than before, but it still depends on relatively shallow aliases, ingredients, and preparation tags
- User confirmation and correction exist conceptually, but are not yet fully first‑class in the stored meal lifecycle
- Ingestion is import‑ready, but not yet a full operational import, curation, and provenance‑review workflow

Not yet complete

- There is still no robust curated review queue for unresolved foods and ambiguous matches
- Component extraction is used as a refinement signal, not yet as a richer structured evidence model
- Mixed meals still collapse to a best‑effort canonical naming strategy instead of a more explicit plated‑meal composition model
- Not all guidance logic consumes enriched risk tags in a fully first‑class way yet
- User correction feedback is not yet fully operationalized into alias and ranking improvements

## Current Strengths

Architectural strengths

- Clean separation between perception, search, reconciliation, and guidance
- Typed contracts between layers
- Deterministic nutrition and glycemic logic
- One canonical food layer shared by perception fallback and recommendation flows
- Reusable enriched meal events for longitudinal use
- Thin API orchestration
- Practical compatibility path for existing consumers
- Confidence‑gated correction path for safer UX

Product strengths

- Singapore hawker‑food support remains first‑class
- Uncertainty is preserved instead of hidden
- Multi‑item perception is represented explicitly
- Visible components can improve dish disambiguation
- Meal records are better suited for trends, summaries, and clinician views
- User confirmation can reduce false normalization without forcing friction on every meal

## Current Gaps and Limitations

Gap 1: Matching quality is improved, but still shallow.

The current ranking logic uses alias similarity, component overlap, preparation compatibility, and light token overlap. It would be stronger with alias priority and alias type metadata, better ingredient‑tag coverage, cuisine‑aware tie‑breaking, explicit dish‑family and variant modeling, and semantic retrieval support.

Gap 2: Portion estimation is still heuristic.

Portions are currently estimated via stored portion references, default portion grams, and fallback unit heuristics. This is acceptable for the current branch, but it is not yet calibrated against image‑derived size or container evidence.

Gap 3: Risk tags are useful but simple.

Current risk tagging focuses on straightforward thresholds and preparation cues. It does not yet fully express disease‑specific glycemic burden, medication‑aware risk amplification, more explicit meal‑balance scoring, or clinician‑facing confidence intervals.

Gap 4: Compatibility bridging still carries legacy complexity.

The system still rebuilds MealState for compatibility. That is a reasonable migration choice, but long term the enriched event should become the primary contract everywhere.

Gap 5: Ingestion is curated, not yet operationalized.

Reduced USDA and Open Food Facts sources are available as ingestion seams, but there is not yet a full maintained workflow for raw source import, reduction rules, manual review, canonical approval lifecycle, update cadence, and provenance policy.

Gap 6: Feedback learning is not yet first‑class.

The design now includes user confirmation and correction, but there is not yet a mature workflow for correction storage, unresolved‑food review queues, alias enrichment from user feedback, and evaluation dataset growth from corrected traffic.

## Recommended Next Improvements

Near term

- Promote finalized enriched meal events further by reducing direct dependence on legacy MealState, exposing match confidence and review state in APIs, and treating compatibility rebuilding as transitional only
- Improve canonical record quality instead of adding more model work by expanding ingredient and preparation tags, adding alias priority and alias type metadata, modeling local variants explicitly, and keeping nutrition and glycemic facts database‑backed
- Build the user confirmation and unresolved‑food curation loop by capturing unresolved labels, persisting user corrections, surfacing review candidates, and feeding reviewed outcomes back into canonical‑food curation
- Add better explainability by persisting why the canonical match won, showing component mismatch and match confidence, preserving source‑dataset provenance, and distinguishing perception confidence from reconciliation confidence

Medium term

- Improve component evidence quality by asking the perception layer for more consistent components, distinguishing garnishes from primary ingredients, capturing sauce and side‑dish cues, and using multi‑item evidence more deliberately
- Improve portion references by maintaining dish‑specific portion tables, supporting beverage volume units, distinguishing portion variants, and calibrating against representative images
- Operationalize ingestion by sourcing and reducing external datasets repeatably, documenting review rules, preserving provenance, and making import jobs idempotent and testable
- Introduce semantic retrieval without changing contracts by adding embedding‑based candidate retrieval, keeping deterministic reconciliation as the final authority, and benchmarking semantic retrieval separately

Longer term

- Separate audit and guidance concerns by preserving raw perception output and benchmarking perception quality, canonical matching quality, and guidance quality independently
- Add clinician‑facing evidence views showing match confidence, perception versus reconciliation confidence, unresolved assumptions, source provenance, and whether a meal was auto‑accepted or user‑corrected
- Consider approximate nutrition only as an explicit fallback product feature, never as a silent synthesis, and only after product‑level review

## Suggested Roadmap

Phase 1: stabilize the shipped architecture

- Extend more consumers to use finalized enriched events first
- Harden validation around perception, search, reconciliation, and confirmation boundaries
- Improve canonical data quality for priority Singapore meals
- Implement confirmation‑state persistence

Phase 2: improve deterministic matching quality

- Better aliases and variant metadata
- Better ingredient and preparation coverage
- Explicit unresolved‑item and correction review loop
- Richer explanation of why a dish was matched

Phase 3: improve product intelligence

- Richer risk tagging
- Better meal scoring
- Disease‑aware explanations built from deterministic enriched data
- Clinician‑facing evidence and provenance views

Phase 4: operationalize ingestion and evaluation

- Repeatable import jobs
- Provenance policy
- Benchmark datasets
- Offline evaluation for perception, retrieval, reconciliation, and guidance separately

## Validation Status

The refactor has been validated with targeted meal‑analysis and downstream‑consumer tests, including perception‑first hawker‑vision behavior, canonical food ingestion and candidate ranking, meal normalization and manual‑review triggers, enriched‑event persistence, and enriched‑event consumption in summaries and recommendation flows.

Repository‑wide validation is still not a clean signal because unrelated pre‑existing failures exist elsewhere in the codebase.

Future validation should also include confidence‑gated confirmation behavior, persistence of user correction flows, correction‑to‑curation feedback behavior, and evaluation splits for perception, search, and reconciliation independently.

## Practical Summary

The meal‑analysis stack should no longer be centered on a model inventing nutrition and advice directly from an image. It should be centered on:

- Typed perception from the image layer
- Canonical food retrieval from the food store
- Deterministic reconciliation and enrichment from the canonical‑food layer
- User confirmation or correction only when confidence requires it

