Here’s an edited version of the plan that incorporates the stronger flow:

perception first

canonical search second

deterministic reconciliation third

user confirmation only where needed

finalized enriched event before persistence and downstream use

I also tightened a few areas so the architecture reads more like a real product/system design doc instead of only an internal refactor note.

Meal Analysis Agents
Purpose

This document explains the target meal-analysis architecture for Dietary Guardian, what is already implemented, and the highest-value next improvements for the meal-analysis stack.

The system is organized around a deliberate split:

perception first

canonical food retrieval and search second

deterministic reconciliation and enrichment third

user confirmation and correction where needed

persistence and downstream care logic after finalization

That split keeps image understanding bounded, keeps nutrition and risk logic auditable, gives users a correction path when confidence is weak, and ensures downstream companion surfaces consume a stable enriched meal event rather than raw model guesses.

Design Principles
1. Perception is not nutrition

The image-capable model should answer only questions that require looking at the image:

what foods are likely present

what visible components are present

rough portion units and counts

visible preparation cues

image quality concerns

confidence and ambiguity

It should not be the source of truth for:

canonical food naming

nutrition totals

glycemic labels

risk tags

patient guidance

clinician-facing conclusions

2. Canonical food search owns candidate retrieval

After perception, the backend should search the canonical food store using deterministic retrieval and ranking signals:

perceived labels

candidate aliases

visible components

preparation cues

token overlap

future semantic retrieval support

The goal of this stage is not yet to finalize nutrition, but to produce strong canonical candidates for reconciliation.

3. Deterministic reconciliation owns food facts

After candidate retrieval, the backend should:

reconcile perception evidence with canonical food candidates

choose the best canonical match when confidence is sufficient

preserve ambiguous or unresolved cases explicitly

estimate grams from portion references

attach deterministic nutrition and glycemic metadata

derive heuristic risk tags

produce a candidate enriched meal event

This stage owns auditable meal normalization.

4. User confirmation is a correction layer, not the primary reasoning layer

User feedback should refine and finalize uncertain outcomes, not replace deterministic normalization.

The confirmation layer should support:

yes: accept the candidate meal event

no: reject and edit the selected food or meal name

edit: adjust portions, components, or item composition

correction capture: feed mismatches back into curation and review workflows

The system should not ask for confirmation when confidence is high and evidence is clean.

5. Guidance should consume finalized enriched meal events

Recommendation, case snapshot, trends, summaries, and clinician-facing logic should work from finalized normalized meal data rather than raw perception output.

Target End-to-End Pipeline
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
Confidence-Gated Interaction Model

The meal-analysis stack should not always require user confirmation.

High-confidence flow

When perception confidence, canonical match confidence, and evidence consistency are all strong:

auto-accept the candidate meal event

persist the finalized enriched meal event directly

optionally allow passive edit afterward

Medium-confidence flow

When the system has a likely match but ambiguity remains:

show the top candidate

surface alternatives when useful

ask the user to confirm or correct

Low-confidence flow

When the image is weak, the match is unresolved, or evidence conflicts:

request explicit user correction

mark for manual review where appropriate

avoid silently inventing nutrition

This keeps UX fast when confidence is high and safe when confidence is weak.

Current End-to-End Pipeline
User Input
  -> HawkerVision perception
  -> MealPerception
  -> ranked canonical food search
  -> deterministic reconciliation
  -> candidate enriched meal event
  -> confidence-based user confirmation when needed
  -> finalized enriched meal event
  -> persistence
  -> downstream consumer systems
Module Map
Vision and perception

src/dietary_guardian/agent/meal_analysis/vision_module.py

Domain contracts

src/dietary_guardian/features/meals/domain/models.py

Application normalization, reconciliation, and enrichment

src/dietary_guardian/features/meals/use_cases.py

Provider/runtime integration

src/dietary_guardian/agent/runtime/llm_factory.py

src/dietary_guardian/agent/runtime/llm_routing.py

src/dietary_guardian/agent/runtime/inference_engine.py

Canonical food search, ranking, and loading logic

src/dietary_guardian/features/recommendations/domain/canonical_food_matching.py

src/dietary_guardian/platform/persistence/food/ingestion.py

Persistence

src/dietary_guardian/platform/persistence/sqlite_repository.py

Compatibility helpers for downstream consumers

src/dietary_guardian/features/meals/presenter.py

Example downstream consumers

src/dietary_guardian/features/meals/api_service.py

src/dietary_guardian/features/recommendations/use_cases.py

src/dietary_guardian/features/companion/core/use_cases.py

Future feedback and review workflows

unresolved-food review queue

user correction store

canonical-food curation workflow

Core Contracts
MealPerception

MealPerception is the bounded output of the perception layer.

It includes:

meal_detected

items

uncertainties

image_quality

confidence_score

Each perceived item is represented by PerceivedMealItem:

label

candidate_aliases

detected_components

portion_estimate

preparation

confidence

This keeps the vision layer constrained to image understanding while still giving search and reconciliation enough evidence to disambiguate dishes.

CandidateMealEvent

CandidateMealEvent is the deterministic output produced after canonical search and reconciliation, before final confirmation.

It should include:

proposed meal name

normalized items

nutrition estimate from canonical records

risk tags

unresolved items

source records

match confidence

review flags

explanation metadata

This is the candidate the system may auto-accept or present to the user for correction.

EnrichedMealEvent

EnrichedMealEvent is the finalized deterministic normalized output used across the rest of the system.

It includes:

meal_name

normalized_items

total_nutrition

risk_tags

unresolved_items

source_records

needs_manual_review

summary

confirmation_status

user_corrections where applicable

Each NormalizedMealItem captures:

detected label

canonical food match

matched alias

match strategy

match confidence

preparation

portion estimate

estimated grams

deterministic item nutrition

risk tags

source dataset

What the Vision Agent Should Do

HawkerVisionModule should use a perception-only system prompt. The prompt should explicitly instruct the model to:

return strict MealPerception

detect likely foods and visible components

estimate coarse portions

describe preparation cues

report confidence and uncertainty

avoid generating nutrition, glycemic claims, risk tags, or advice

Important behavior

low-confidence or ambiguous captures should return clarification-style perception responses

test-provider flows should emit deterministic MealPerception payloads for stable tests

image-quality issues should be surfaced explicitly

the perception layer should remain bounded even if future models become more capable

What the Canonical Search Layer Should Do

The canonical search layer should:

search canonical food records using perceived labels and aliases

incorporate detected components and preparation cues

rank dish candidates deterministically

support future semantic retrieval without changing downstream contracts

return top candidates and match evidence for reconciliation

Current ranking signals

Canonical search should remain dish-first, with refinement from additional evidence:

exact and partial alias matches weighted highest

detected component overlap adjusting score

preparation compatibility adjusting score

token overlap used as a weak tie-breaker

Later improvements may include:

alias priority metadata

alias type metadata

cuisine-aware tie-breaking

dish-family and variant modeling

semantic vector retrieval for fuzzy recall

What the Deterministic Reconciliation Layer Should Do

The feature layer in features/meals/use_cases.py should handle:

legacy-to-perception conversion when needed

candidate reconciliation against canonical search results

portion-unit to gram estimation

deterministic nutrition scaling from canonical records

heuristic risk-tag derivation

component-mismatch detection

meal-level nutrition summation

unresolved-item handling

CandidateMealEvent construction

EnrichedMealEvent finalization

compatibility MealState rebuilding where still required

MealRecognitionRecord construction

Current normalization behavior

For each perceived item:

collect the observed label, candidate aliases, detected components, and preparation cue

retrieve and rank canonical food candidates

pick the best candidate when it clears the match threshold

estimate grams from:

stored portion references

default portion grams

fallback unit heuristics

scale nutrition from the matched canonical record

derive heuristic risk tags

add component_mismatch when visible evidence conflicts with the canonical record

keep the item unresolved when no safe canonical match exists

User Confirmation and Correction Layer
Purpose

The user confirmation layer exists to finalize uncertain cases safely and to improve the system over time.

Supported actions

confirm the candidate meal event

reject the proposed dish and select another

edit portion estimates

add or remove meal items

flag unclear images or incorrect detections

Confirmation policy

The system should:

auto-accept when confidence is high and no review flags are present

request confirmation when match confidence is moderate

require correction when evidence is weak or unresolved

Feedback capture

Corrections should be stored for:

unresolved-food curation

alias expansion

ranking improvement

future evaluation datasets

review-queue prioritization

Current Manual-Review Rules

Normalization should mark a meal for manual review when any of the following is true:

the vision layer already requested manual review

one or more items are unresolved

any matched item has low match confidence

component or preparation evidence conflicts with the chosen canonical food

image quality is poor

image quality is only fair and perception confidence is also low

user correction conflicts strongly with the top canonical match

That behavior is intentional. The system should surface uncertainty rather than silently force a confident nutrition result from weak evidence.

Canonical Food Layer

The canonical food layer stabilizes meal naming, nutrition logic, glycemic metadata, and food provenance across perception and recommendation flows.

Current canonical model

CanonicalFoodRecord currently supports:

food_id

title

aliases

aliases_normalized

slot

venue_type

cuisine_tags

ingredient_tags

preparation_tags

nutrition

health_tags

risk_tags

glycemic_index_label

glycemic_index_value

disease_advice

alternatives

serving_size

default_portion_grams

portion_references

source_dataset

source_type

Current data sources

The active canonical food layer is assembled from:

DEFAULT_MEAL_CATALOG

Singapore-local seed data in src/dietary_guardian/data/food/sg_hawker_food.json

optional reduced USDA data in src/dietary_guardian/data/food/usda_foods.json

optional reduced Open Food Facts data in src/dietary_guardian/data/food/open_food_facts_products.json

Current ingestion posture

The code is wired for curated reduced source files rather than raw source mirrors. That is the right trade-off for the current hackathon branch:

easier to reason about

easier to validate

easier to keep deterministic

compatible with future import and review workflows

Persistence Model

Meal persistence should store more than the legacy meal state.

Meal record fields

MealRecognitionRecord should support:

meal_state

meal_perception

candidate_enriched_event

enriched_event

confirmation_status

user_corrections

Database support

SQLite support should include:

richer meal-record JSON storage

canonical food persistence

food aliases

portion references

confirmation and correction records

This gives the system a path toward:

consistent meal history

repeatable analytics

auditable perception-versus-search-versus-reconciliation comparisons

clinician-facing evidence later without reworking the storage model

Downstream Consumer Strategy

The system should use helper utilities to let downstream services prefer finalized enriched data while still supporting legacy records where necessary.

Utility accessors

Current helper functions include:

meal_display_name()

meal_nutrition()

meal_ingredients()

meal_nutrition_profile()

meal_confidence()

meal_identification_method()

meal_risk_tags()

Downstream adoption target

These consumers should prefer finalized enriched meal events:

daily nutrition summary

weekly nutrition summary

metric trend generation

case snapshot assembly

recommendation generation

recommendation-agent temporal and substitution flows

They should not rely directly on raw perception output except for audit or evaluation views.

Current Progress
Completed

perception-first meal domain contracts were added

HawkerVisionModule was refactored to emit bounded perception instead of model-generated nutrition or advice

deterministic normalization and enrichment use cases were added

canonical food records now support aliases, portion references, default portions, glycemic metadata, and risk tags

the canonical food layer now merges default meal-catalog seeds, Singapore hawker data, and optional reduced external datasets

meal normalization now uses ranked candidate selection instead of label-only lookup

component and preparation evidence now influence canonical dish selection

component and preparation mismatches now escalate meals to manual review

SQLite persistence was extended for perception and enriched-event storage

compatibility helpers were added for downstream services

downstream consumers were updated to prefer enriched meal events

targeted tests were added and updated for:

hawker-vision perception flow

canonical food ranking behavior

meal normalization and manual-review triggers

ingestion reducers

persistence round-trip

enriched-event consumer behavior

Partially complete

compatibility still relies on rebuilding legacy MealState

risk-tag derivation is deterministic but still heuristic rather than clinically calibrated

canonical matching is stronger than before, but it still depends on relatively shallow aliases, ingredients, and preparation tags

user confirmation and correction exist conceptually, but are not yet fully first-class in the stored meal lifecycle

ingestion is import-ready, but not yet a full operational import, curation, and provenance-review workflow

Not yet complete

there is still no robust curated review queue for unresolved foods and ambiguous matches

component extraction is used as a refinement signal, not yet as a richer structured evidence model

mixed meals still collapse to a best-effort canonical naming strategy instead of a more explicit plated-meal composition model

not all guidance logic consumes enriched risk tags in a fully first-class way yet

user correction feedback is not yet fully operationalized into alias and ranking improvements

Current Strengths
Architectural strengths

clean separation between perception, search, reconciliation, and guidance

typed contracts between layers

deterministic nutrition and glycemic logic

one canonical food layer shared by perception fallback and recommendation flows

reusable enriched meal events for longitudinal use

thin API orchestration

practical compatibility path for existing consumers

confidence-gated correction path for safer UX

Product strengths

Singapore hawker-food support remains first-class

uncertainty is preserved instead of hidden

multi-item perception is represented explicitly

visible components can improve dish disambiguation

meal records are better suited for trends, summaries, and clinician views

user confirmation can reduce false normalization without forcing friction on every meal

Current Gaps and Limitations
1. Matching quality is improved, but still shallow

The current ranking logic uses:

alias similarity

component overlap

preparation compatibility

light token overlap

That is a solid deterministic base, but it is still weaker than a more curated matcher with:

alias priority and alias type metadata

better ingredient-tag coverage

cuisine-aware tie-breaking

explicit dish-family and variant modeling

semantic retrieval support

2. Portion estimation is still heuristic

Portions are currently estimated via:

stored portion references

default portion grams

fallback unit heuristics

This is acceptable for the current branch, but it is not yet calibrated against image-derived size or container evidence.

3. Risk tags are useful but simple

Current risk tagging focuses on straightforward thresholds and preparation cues. It does not yet fully express:

disease-specific glycemic burden

medication-aware risk amplification

more explicit meal-balance scoring

clinician-facing confidence intervals

4. Compatibility bridging still carries legacy complexity

The system still rebuilds MealState for compatibility. That is a reasonable migration choice, but long term the enriched event should become the primary contract everywhere.

5. Ingestion is curated, not yet operationalized

Reduced USDA and Open Food Facts sources are available as ingestion seams, but there is not yet a full maintained workflow for:

raw source import

reduction rules

manual review

canonical approval lifecycle

update cadence and provenance policy

6. Feedback learning is not yet first-class

The design now includes user confirmation and correction, but there is not yet a mature workflow for:

correction storage

unresolved-food review queues

alias enrichment from user feedback

evaluation dataset growth from corrected traffic

Recommended Next Improvements
Near term
1. Promote finalized enriched meal events further

reduce direct dependence on legacy MealState

expose match confidence, confirmation status, and review state more directly in APIs and UI

treat compatibility rebuilding as transitional only

2. Improve canonical record quality instead of adding more model work

expand ingredient tags and preparation tags on high-volume dishes

add alias priority and alias type metadata

model common local variants explicitly

keep nutrition and glycemic facts database-backed

3. Build the user confirmation and unresolved-food curation loop

capture unresolved labels and low-confidence matches for review

persist user corrections and rejected candidates

surface review candidates from production traffic or demo runs

feed reviewed outcomes back into canonical-food curation

4. Add better explainability for meal analysis

persist why the canonical match won

show component mismatch and match confidence clearly

preserve source-dataset provenance in user and clinician surfaces where useful

distinguish perception confidence from reconciliation confidence

Medium term
5. Improve component evidence quality

ask the perception layer for more consistent component extraction

distinguish garnishes from primary ingredients

capture sauce, gravy, and side-dish cues explicitly

use multi-item evidence more deliberately before collapsing to a single meal name

6. Improve portion references

maintain dish-specific portion tables

support beverage volume units separately from solid-food grams

distinguish default portion from small and large variants

calibrate against representative meal-image examples

7. Operationalize ingestion

source and reduce external food datasets repeatably

document review rules

preserve provenance and update timestamps

make import jobs idempotent and testable

8. Introduce semantic retrieval without changing contracts

add embedding-based candidate retrieval for fuzzy labels and aliases

keep deterministic reconciliation as the final authority

benchmark semantic retrieval separately from deterministic ranking

Longer term
9. Separate audit and guidance concerns more clearly

preserve raw perception output for evaluation

benchmark perception quality separately from canonical matching quality

benchmark matching quality separately from care-guidance quality

10. Add clinician-facing evidence views

show canonical match confidence

show perception confidence versus reconciliation confidence

show unresolved assumptions

show source provenance for nutrition values

show whether a meal was auto-accepted or user-corrected

11. Consider approximate nutrition mode only as an explicit fallback product feature

do not silently synthesize nutrition from components today

if approximate mode is added later, keep it clearly labeled and separate from canonical matches

require product-level review before exposing it in care-facing workflows

Suggested Roadmap
Phase 1: stabilize the shipped architecture

extend more consumers to use finalized enriched events first

harden validation around perception, search, reconciliation, and confirmation boundaries

improve canonical data quality for priority Singapore meals

implement confirmation-state persistence

Phase 2: improve deterministic matching quality

better aliases and variant metadata

better ingredient and preparation coverage

explicit unresolved-item and correction review loop

richer explanation of why a dish was matched

Phase 3: improve product intelligence

richer risk tagging

better meal scoring

disease-aware explanations built from deterministic enriched data

clinician-facing evidence and provenance views

Phase 4: operationalize ingestion and evaluation

repeatable import jobs

provenance policy

benchmark datasets

offline evaluation for perception, retrieval, reconciliation, and guidance separately

Validation Status

The refactor has been validated with targeted meal-analysis and downstream-consumer tests, including:

perception-first hawker-vision behavior

canonical food ingestion and candidate ranking

meal normalization and manual-review triggers

enriched-event persistence

enriched-event consumption in summaries and recommendation flows

Repository-wide validation is still not a clean signal because unrelated pre-existing failures exist elsewhere in the codebase.

Future validation should also include:

confidence-gated confirmation behavior

persistence of user correction flows

correction-to-curation feedback behavior

evaluation splits for perception, search, and reconciliation independently

Practical Summary

The meal-analysis stack should no longer be centered on a model inventing nutrition and advice directly from an image. It should be centered on:

typed perception from the image layer

canonical food retrieval from the food store

deterministic reconciliation and enrichment from the canonical-food layer

user confirmation or correction only when confidence requires it

downstream care logic built on finalized enriched meal events

That is the correct architecture for a trustworthy hackathon demo and a stronger base for future clinician-facing and longitudinal nutrition features.