# Meal Analysis Agents

## Purpose
This document explains the current meal-analysis architecture, what is already implemented, and the most valuable next improvements for the Dietary Guardian meal-analysis stack.

The system is now organized around a deliberate split:
- vision and perception first
- deterministic canonical-food normalization second
- care guidance, recommendations, and summaries after enrichment

That split keeps image understanding bounded, keeps nutrition and risk logic auditable, and gives downstream companion surfaces a stable enriched meal event instead of raw model guesses.

## Design Principles

### 1. Perception is not nutrition
The image-capable model should answer only questions that require looking at the image:
- what foods are likely present
- what visible components are present
- rough portion units and counts
- visible preparation cues
- image quality concerns
- confidence and ambiguity

It should not be the source of truth for:
- canonical food naming
- nutrition totals
- glycemic labels
- risk tags
- patient guidance
- clinician-facing conclusions

### 2. Deterministic enrichment owns food facts
After perception, the backend should:
- map visible foods to canonical food records
- attach deterministic nutrition and glycemic metadata
- estimate grams from portion references
- derive heuristic risk tags
- preserve unresolved or ambiguous cases explicitly
- store a reusable enriched meal event

### 3. Guidance should consume enriched meal events
Recommendation, case snapshot, trends, and clinician-facing logic should work from normalized meal data rather than from raw vision output.

## Current End-to-End Pipeline

```text
Image or text input
  -> HawkerVision perception
  -> MealPerception (typed, bounded JSON)
  -> ranked canonical food matching
  -> portion-to-gram estimation
  -> deterministic nutrition scaling
  -> risk-tag enrichment
  -> EnrichedMealEvent
  -> persistence
  -> downstream summaries, recommendations, and clinician context
```

## Module Map

### Vision and perception
- `src/dietary_guardian/agents/vision.py`

### Domain contracts
- `src/dietary_guardian/domain/meals/models.py`

### Application normalization and enrichment
- `src/dietary_guardian/application/meals/use_cases.py`

### Provider/runtime integration
- `src/dietary_guardian/llm/factory.py`
- `src/dietary_guardian/llm/routing.py`
- `src/dietary_guardian/agents/executor.py`

### Canonical food seed, ranking, and loading logic
- `src/dietary_guardian/services/canonical_food_service.py`
- `src/dietary_guardian/infrastructure/food/ingestion.py`

### Persistence
- `src/dietary_guardian/infrastructure/persistence/sqlite_repository.py`

### Compatibility helpers for downstream consumers
- `src/dietary_guardian/services/meal_record_utils.py`

### Example downstream consumers
- `src/dietary_guardian/services/daily_nutrition_service.py`
- `src/dietary_guardian/services/weekly_nutrition_service.py`
- `src/dietary_guardian/services/recommendation_service.py`
- `src/dietary_guardian/services/recommendation_agent_service.py`
- `src/dietary_guardian/application/case_snapshot/use_cases.py`
- `src/dietary_guardian/services/metrics_trend_service.py`

## Core Contracts

### MealPerception
`MealPerception` is the bounded output of the perception layer.

It includes:
- `meal_detected`
- `items`
- `uncertainties`
- `image_quality`
- `confidence_score`

Each perceived item is represented by `PerceivedMealItem`:
- `label`
- `candidate_aliases`
- `detected_components`
- `portion_estimate`
- `preparation`
- `confidence`

This keeps the vision layer constrained to image understanding while still giving normalization enough evidence to disambiguate dishes.

### EnrichedMealEvent
`EnrichedMealEvent` is the deterministic normalized output used across the rest of the system.

It includes:
- `meal_name`
- `normalized_items`
- `total_nutrition`
- `risk_tags`
- `unresolved_items`
- `source_records`
- `needs_manual_review`
- `summary`

Each `NormalizedMealItem` captures:
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

## What the Vision Agent Currently Does
`HawkerVisionModule` now uses a perception-only system prompt. The prompt explicitly instructs the model to:
- return strict `MealPerception`
- detect likely foods and visible components
- estimate coarse portions
- describe preparation cues
- report confidence and uncertainty
- avoid generating nutrition, glycemic claims, risk tags, or advice

### Important current behavior
- low-confidence or ambiguous captures return clarification-style responses
- test-provider flows emit deterministic `MealPerception` payloads for stable tests
- `analyze_dish()` always routes successful perception through deterministic normalization before returning
- `analyze_and_record()` persists both perception and enriched normalization output
- the compatibility `MealState` still exists, but it is now rebuilt from the enriched event and prior perception rather than treated as the primary architecture target

## What the Deterministic Layer Currently Does
The application layer in `application/meals/use_cases.py` now handles:
- legacy-to-perception conversion when needed
- ranked canonical food candidate selection
- portion-unit to gram estimation
- deterministic nutrition scaling from canonical records
- heuristic risk-tag derivation
- component-mismatch detection
- meal-level nutrition summation
- unresolved-item handling
- `EnrichedMealEvent` construction
- compatibility `MealState` rebuilding
- `MealRecognitionRecord` construction

### Current normalization behavior
For each perceived item:
1. collect the observed label, candidate aliases, detected components, and preparation cue
2. rank canonical food candidates using deterministic scoring
3. pick the best candidate when it clears the match threshold
4. estimate grams from:
   - stored portion references
   - default portion grams
   - fallback unit heuristics
5. scale nutrition from the matched canonical record
6. derive heuristic risk tags
7. add `component_mismatch` when visible evidence conflicts with the canonical record
8. keep the item unresolved when no safe canonical match exists

### Current ranking signals
Canonical matching is now dish-first, with refinement from additional evidence:
- exact and partial alias matches are weighted highest
- detected component overlap adjusts the candidate score
- preparation compatibility adjusts the candidate score
- token overlap provides a weak final tie-breaker

This is still deterministic. The model does not invent fallback nutrition when the match is weak.

### Current manual-review rules
Normalization marks a meal for manual review when any of the following is true:
- the vision layer already requested manual review
- one or more items are unresolved
- any matched item has low match confidence
- component or preparation evidence conflicts with the chosen canonical food
- image quality is poor
- image quality is only fair and perception confidence is also low

That behavior is intentional. The system should surface uncertainty rather than silently force a confident nutrition result from weak evidence.

## Canonical Food Layer
The canonical food layer stabilizes meal naming, nutrition logic, glycemic metadata, and food provenance across perception and recommendation flows.

### Current canonical model
`CanonicalFoodRecord` currently supports:
- `food_id`
- `title`
- `aliases`
- `aliases_normalized`
- `slot`
- `venue_type`
- `cuisine_tags`
- `ingredient_tags`
- `preparation_tags`
- `nutrition`
- `health_tags`
- `risk_tags`
- `glycemic_index_label`
- `glycemic_index_value`
- `disease_advice`
- `alternatives`
- `serving_size`
- `default_portion_grams`
- `portion_references`
- `source_dataset`
- `source_type`

### Current data sources
The active canonical food layer is assembled from:
- `DEFAULT_MEAL_CATALOG`
- Singapore-local seed data in `src/dietary_guardian/data/food/sg_hawker_food.json`
- optional reduced USDA data in `src/dietary_guardian/data/food/usda_foods.json`
- optional reduced Open Food Facts data in `src/dietary_guardian/data/food/open_food_facts_products.json`

### Current ingestion posture
The code is wired for curated reduced source files rather than raw source mirrors. That is the right trade-off for the current hackathon branch:
- easier to reason about
- easier to validate
- easier to keep deterministic
- compatible with future import and review workflows

## Persistence Model
Meal persistence now stores more than the legacy meal state.

### Meal record fields
`MealRecognitionRecord` supports:
- `meal_state`
- `meal_perception`
- `enriched_event`

### Database support
SQLite support includes:
- richer meal-record JSON storage
- canonical food persistence
- food aliases
- portion references

This gives the system a path toward:
- consistent meal history
- repeatable analytics
- auditable perception-versus-normalization comparisons
- clinician-facing evidence later without reworking the storage model

## Downstream Consumer Strategy
The system uses `meal_record_utils.py` to let downstream services prefer enriched data while still supporting legacy records.

### Utility accessors
Current helper functions include:
- `meal_display_name()`
- `meal_nutrition()`
- `meal_ingredients()`
- `meal_nutrition_profile()`
- `meal_confidence()`
- `meal_identification_method()`
- `meal_risk_tags()`

### Current downstream adoption
These consumers already prefer enriched meal events:
- daily nutrition summary
- weekly nutrition summary
- metric trend generation
- case snapshot assembly
- recommendation generation
- recommendation-agent temporal and substitution flows

## Current Progress

### Completed
- perception-first meal domain contracts were added
- `HawkerVisionModule` was refactored to emit bounded perception instead of model-generated nutrition or advice
- deterministic normalization and enrichment use cases were added
- canonical food records now support aliases, portion references, default portions, glycemic metadata, and risk tags
- the canonical food layer now merges default meal-catalog seeds, Singapore hawker data, and optional reduced external datasets
- meal normalization now uses ranked candidate selection instead of label-only lookup
- component and preparation evidence now influence canonical dish selection
- component and preparation mismatches now escalate meals to manual review
- SQLite persistence was extended for perception and enriched-event storage
- compatibility helpers were added for downstream services
- downstream consumers were updated to prefer enriched meal events
- targeted tests were added and updated for:
  - hawker-vision perception flow
  - canonical food ranking behavior
  - meal normalization and manual-review triggers
  - ingestion reducers
  - persistence round-trip
  - enriched-event consumer behavior

### Partially complete
- compatibility still relies on rebuilding legacy `MealState`
- risk-tag derivation is deterministic but still heuristic rather than clinically calibrated
- canonical matching is stronger than before, but it still depends on relatively shallow aliases, ingredients, and preparation tags
- ingestion is import-ready, but not yet a full operational import, curation, and provenance-review workflow

### Not yet complete
- there is still no robust curated review queue for unresolved foods and ambiguous matches
- component extraction is used as a refinement signal, not yet as a richer structured evidence model
- mixed meals still collapse to a best-effort canonical naming strategy instead of a more explicit plated-meal composition model
- not all guidance logic consumes enriched risk tags in a fully first-class way yet

## Current Strengths

### Architectural strengths
- clean separation between perception and enrichment
- typed contracts between layers
- deterministic nutrition and glycemic logic
- one canonical food layer shared by perception fallback and recommendation flows
- reusable enriched meal events for longitudinal use
- thin API orchestration
- practical compatibility path for existing consumers

### Product strengths
- Singapore hawker-food support remains first-class
- uncertainty is preserved instead of hidden
- multi-item perception is represented explicitly
- visible components can now improve dish disambiguation
- meal records are better suited for trends, summaries, and clinician views

## Current Gaps and Limitations

### 1. Matching quality is improved, but still shallow
The current ranking logic uses:
- alias similarity
- component overlap
- preparation compatibility
- light token overlap

That is a solid deterministic base, but it is still weaker than a more curated matcher with:
- alias priority and alias type metadata
- better ingredient-tag coverage
- cuisine-aware tie-breaking
- explicit dish-family and variant modeling

### 2. Portion estimation is still heuristic
Portions are currently estimated via:
- stored portion references
- default portion grams
- fallback unit heuristics

This is acceptable for the current branch, but it is not yet calibrated against image-derived size or container evidence.

### 3. Risk tags are useful but simple
Current risk tagging focuses on straightforward thresholds and preparation cues. It does not yet fully express:
- disease-specific glycemic burden
- medication-aware risk amplification
- more explicit meal-balance scoring
- clinician-facing confidence intervals

### 4. Compatibility bridging still carries legacy complexity
The system still rebuilds `MealState` for compatibility. That is a reasonable migration choice, but long term the enriched event should become the primary contract everywhere.

### 5. Ingestion is curated, not yet operationalized
Reduced USDA and Open Food Facts sources are available as ingestion seams, but there is not yet a full maintained workflow for:
- raw source import
- reduction rules
- manual review
- canonical approval lifecycle
- update cadence and provenance policy

## Recommended Next Improvements

### Near term

#### 1. Promote enriched meal events further
- reduce direct dependence on legacy `MealState`
- expose match confidence and review state more directly in APIs and UI
- treat compatibility rebuilding as transitional only

#### 2. Improve canonical record quality instead of adding more model work
- expand ingredient tags and preparation tags on high-volume dishes
- add alias priority and alias type metadata
- model common local variants explicitly
- keep nutrition and glycemic facts database-backed

#### 3. Build an unresolved-food curation loop
- capture unresolved labels and low-confidence matches for review
- surface review candidates from production traffic or demo runs
- feed reviewed outcomes back into canonical-food curation

#### 4. Add better explainability for meal analysis
- persist why the canonical match won
- show component mismatch and match confidence clearly
- preserve source-dataset provenance in user and clinician surfaces where useful

### Medium term

#### 5. Improve component evidence quality
- ask the perception layer for more consistent component extraction
- distinguish garnishes from primary ingredients
- capture sauce, gravy, and side-dish cues explicitly
- use multi-item evidence more deliberately before collapsing to a single meal name

#### 6. Improve portion references
- maintain dish-specific portion tables
- support beverage volume units separately from solid-food grams
- distinguish default portion from small and large variants
- calibrate against representative meal-image examples

#### 7. Operationalize ingestion
- source and reduce external food datasets repeatably
- document review rules
- preserve provenance and update timestamps
- make import jobs idempotent and testable

### Longer term

#### 8. Separate audit and guidance concerns more clearly
- preserve raw perception output for evaluation
- benchmark perception quality separately from canonical matching quality
- benchmark matching quality separately from care-guidance quality

#### 9. Add clinician-facing evidence views
- show canonical match confidence
- show perception confidence versus normalization confidence
- show unresolved assumptions
- show source provenance for nutrition values

#### 10. Consider approximate nutrition mode only as an explicit fallback product feature
- do not silently synthesize nutrition from components today
- if approximate mode is added later, keep it clearly labeled and separate from canonical matches
- require product-level review before exposing it in care-facing workflows

## Suggested Roadmap

### Phase 1: stabilize the shipped architecture
- extend more consumers to use enriched events first
- harden validation around perception and normalization boundaries
- improve canonical data quality for priority Singapore meals

### Phase 2: improve deterministic matching quality
- better aliases and variant metadata
- better ingredient and preparation coverage
- explicit unresolved-item review loop
- richer explanation of why a dish was matched

### Phase 3: improve health intelligence
- richer risk tagging
- better meal scoring
- disease-aware explanations built from deterministic enriched data
- clinician-facing evidence and provenance views

### Phase 4: operationalize ingestion and evaluation
- repeatable import jobs
- provenance policy
- benchmark datasets
- offline evaluation for perception, normalization, and guidance separately

## Validation Status
The refactor has been validated with targeted meal-analysis and downstream-consumer tests, including:
- perception-first hawker-vision behavior
- canonical food ingestion and candidate ranking
- meal normalization and manual-review triggers
- enriched-event persistence
- enriched-event consumption in summaries and recommendation flows

Repository-wide validation is still not a clean signal because unrelated pre-existing failures exist elsewhere in the codebase.

## Practical Summary
The meal-analysis stack is no longer centered on a model inventing nutrition and advice directly from an image. It is now centered on:
- typed perception from the image layer
- deterministic normalization and enrichment from the canonical-food layer
- downstream care logic built on enriched meal events

That is the correct architecture for a trustworthy hackathon demo and a stronger base for future clinician-facing and longitudinal nutrition features.
