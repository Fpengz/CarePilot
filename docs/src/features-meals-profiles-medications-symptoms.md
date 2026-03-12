# Dietary Guardian Module Reference Documentation

## Overview

This documentation covers the core modules of the **Dietary Guardian** feature system at `src/dietary_guardian/features/`. The system is organized into four main features:
- **Meals**: Meal recognition, nutrition analysis, and summaries
- **Profiles**: Health profiles and onboarding workflows
- **Medications**: Medication regimens and adherence tracking
- **Symptoms**: Symptom check-ins and safety evaluation

---

## 1. MEALS FEATURE

### 1.1 Module Overview
The meals feature provides:
- Image-based meal analysis and recognition
- Nutrition profiling and risk assessment
- Daily/weekly nutrition summaries
- Meal history management

---

### 1.2 `features/meals/__init__.py`

**Entrypoint** - Empty module. **Exports**: `[]`

---

### 1.3 `features/meals/api_service.py`

**Purpose**: API-level meal orchestration use cases bridging FastAPI with domain layer.

#### Classes & Models

| Name | Type | Description |
|------|------|-------------|
| `_ArbitrationDecision` | BaseModel | LLM output for label reconciliation |
| - `chosen_label` | str | Selected food label |
| - `confidence` | float (0.0-1.0) | Confidence score |
| - `rationale` | str \| None | Explanation |

#### Functions

| Function | Signature | Returns | Purpose |
|----------|-----------|---------|---------|
| `analyze_meal` | `(request, deps, session, file, provider, meal_text)` | `MealAnalyzeResponse` | Main meal analysis pipeline: upload image → vision analysis → dietary claim extraction → label arbitration → nutrition profiling |
| `list_meal_records` | `(deps, user_id, limit, cursor)` | `MealRecordsResponse` | Paginated list of validated meal events |
| `get_daily_summary` | `(deps, user_id, summary_date)` | `MealDailySummaryResponse` | Daily nutrition totals vs. targets |
| `get_weekly_summary` | `(deps, user_id, week_start)` | `MealWeeklySummaryResponse` | Weekly meal breakdown by day |
| `_build_hawker_vision_module` | `(provider, food_store)` | HawkerVisionModule | Dynamically loads meal analysis vision module |
| `_extract_dietary_claims` | `(text)` | `DietaryClaims` | Parses user text for food labels, portions, preparation |
| `_context_snapshot` | `(session)` | `ContextSnapshot` | Extracts user context from session |
| `_claim_perception` | `(labels, confidence)` | `MealPerception` | Converts dietary claims to perception structure |
| `_arbitrate_label` | `(vision_labels, claim_labels, user_text, provider)` | `_ArbitrationDecision \| None` | LLM-based reconciliation of conflicting labels |
| `_parse_cursor` | `(cursor)` | int | Decodes pagination cursor |

#### Key Workflows

**`analyze_meal()` Pipeline**:
1. Validate file (size, format, MIME type)
2. Downscale image if needed
3. Build capture envelope for deduplication
4. Load vision analysis agent
5. Run vision analysis with LLM (timeout-controlled)
6. Extract dietary claims from user text
7. Arbitrate conflicts between vision and claims
8. Normalize nutrition across food store
9. Build validated meal event & nutrition risk profile
10. Persist to stores
11. Trigger meal analysis workflow

---

### 1.4 `features/meals/deps.py`

**Purpose**: Dependency injection container for meal operations.

#### Classes

```python
@dataclass(frozen=True)
class MealDeps:
    settings: Settings          # AppSettings
    stores: AppStores           # Persistence layer
    coordinator: WorkflowCoordinator  # Workflow orchestration
```

---

### 1.5 `features/meals/presenter.py`

**Purpose**: Transform meal analysis results into agent output envelopes.

#### Functions

| Function | Returns | Purpose |
|----------|---------|---------|
| `build_meal_analysis_output` | `AgentOutputEnvelope` | Projects `VisionResult` into audit-ready output with decision, presentation message, and trace metadata |

#### Output Structure
- **DomainDecision**: meal_analysis type, confidence score, policy flags
- **PresentationMessage**: UI-ready summary with severity level
- **AuditRecord**: Request/correlation IDs, model version
- **AgentExecutionTrace**: Execution metadata

---

### 1.6 `features/meals/schemas.py`

**Purpose**: Pydantic models for API responses.

#### Classes

| Class | Fields | Purpose |
|-------|--------|---------|
| `DailyNutritionTotalsResponse` | calories, sugar_g, sodium_mg, protein_g, fiber_g | Nutrition aggregate |
| `DailyNutritionInsightResponse` | code, title, summary, actions | Pattern insight |
| `MealDailySummaryResponse` | date, meal_count, last_logged_at, consumed, targets, remaining, insights, recommendation_hints | Daily nutrition report |

---

### 1.7 `features/meals/service.py`

**Purpose**: Internal re-exports of main meal use cases.

**Exports**:
- `analyze_meal`
- `build_meal_analysis_output`
- `build_meal_record`
- `get_daily_summary`
- `get_weekly_summary`
- `list_meal_records`
- `normalize_vision_result`

---

### 1.8 `features/meals/use_cases.py`

**Purpose**: Domain-level meal normalization and enrichment logic.

#### Constants

```python
_UNIT_GRAMS = {
    "bowl": 400.0, "cup": 250.0, "glass": 250.0, "ml": 1.0,
    "piece": 120.0, "plate": 350.0, "portion": 300.0,
    "serving": 300.0, "set": 450.0
}
```

#### Core Functions

| Function | Signature | Returns | Purpose |
|----------|-----------|---------|---------|
| `normalize_vision_result` | `(vision_result, food_store, locale)` | `VisionResult` | Enhance vision result with normalized items, enriched event, nutrition totals |
| `build_meal_record` | `(image_input, user_id, vision_result, request_id)` | `MealRecognitionRecord` | Create persistent meal record from analysis |
| `_normalize_item` | `(food_store, locale, item)` | `NormalizedMealItem` | Match perceived item to canonical food, calculate nutrition |
| `_legacy_perception_from_state` | `(state)` | `MealPerception` | Convert legacy MealState to perception model |
| `_nutrition_scale` | `(base, factor)` | `MealNutritionProfile` | Scale nutrition profile by portion factor |
| `_sum_nutrition` | `(items)` | `MealNutritionProfile` | Aggregate nutrition across items |
| `_compose_meal_name` | `(normalized_items, fallback)` | str | Synthesize meal name from item labels |
| `_estimate_grams` | `(estimate, default_portion_grams, portion_references)` | float \| None | Convert portion estimate to grams |
| `_portion_factor` | `(estimate, estimated_grams, default_portion_grams)` | float | Calculate scaling factor for nutrition |
| `_map_portion_size` | `(items)` | `PortionSize` | Classify portion as SMALL/STANDARD/LARGE/FAMILY |
| `_pick_glycemic_label` | `(items, food_store, locale)` | `GlycemicIndexLevel` | Determine glycemic index from items |
| `_heuristic_risk_tags` | `(preparation, nutrition, base_tags)` | list[str] | Generate risk tags based on nutrition & preparation |

#### Matching Strategy
- **exact_alias**: Food label matches canonical name exactly (confidence 0.95)
- **partial_alias**: Label matches canonical name partially (confidence 0.82)
- **fuzzy_alias**: Ranking score ≥ 0.55 (confidence = min(0.8, ranking_score))
- **unmatched**: No match found (confidence = min(item.confidence, 0.5))

---

### 1.9 `features/meals/domain/agent_schemas.py`

**Purpose**: Typed I/O contracts for meal analysis agents.

#### Classes

| Class | Fields | Purpose |
|-------|--------|---------|
| `DietaryAgentInput` | user: UserProfile, meal: MealEvent | Dietary reasoning request |
| `MealAnalysisAgentInput` | image_input, user_id, request_id, correlation_id, persist_record | Meal analysis request |
| `MealAnalysisAgentOutput` | vision_result: VisionResult, meal_record: MealRecognitionRecord \| None | Agent output envelope |

---

### 1.10 `features/meals/domain/daily_summary.py`

**Purpose**: Daily nutrition summary calculations with insights generation.

#### Functions

| Function | Signature | Returns | Purpose |
|----------|-----------|---------|---------|
| `build_daily_nutrition_summary` | `(profile, meal_history, summary_date, timezone_name)` | `DailyNutritionSummary` | Generate daily report with consumed/target/remaining |
| `_sum_records` | `(records)` | `NutritionTotals` | Aggregate nutrition from meal records |
| `_build_insights` | `(profile, meal_history, summary_date, timezone_name)` | list[NutritionInsight] | Generate pattern-based insights from 7-day window |
| `_recommendation_hints` | `(insights)` | list[str] | Extract actionable hint codes from insights |

#### Insight Codes Generated
- `low_protein_pattern`: avg < 18g or < 40% meals ≥ 20g
- `low_fiber_pattern`: avg < 5g
- `high_sodium_pattern`: avg > 90% daily limit OR ≥ 3 meals > 900mg
- `high_sugar_pattern`: avg > 90% daily limit OR ≥ 3 meals > 15g
- `high_calorie_pattern`: avg > 110% daily target
- `repetitive_meal_pattern`: same dish ≥ 3 times in 7 days

---

### 1.11 `features/meals/domain/meal_record_accessors.py`

**Purpose**: Accessor functions for extracting properties from meal records.

#### Functions

| Function | Parameter | Returns | Purpose |
|----------|-----------|---------|---------|
| `meal_display_name` | `MealRecognitionRecord` | str | Get enriched or legacy meal name |
| `meal_nutrition` | `MealRecognitionRecord` | `Nutrition` | Get total nutrition (enriched or legacy) |
| `meal_ingredients` | `MealRecognitionRecord` | list[Ingredient] | Get normalized or legacy ingredients |
| `meal_nutrition_profile` | `MealRecognitionRecord` | `MealNutritionProfile` | Get new-format nutrition profile |
| `meal_confidence` | `MealRecognitionRecord` | float | Get perception or state confidence |
| `meal_identification_method` | `MealRecognitionRecord` | str | Get analysis method (AI_Flash, HPB_Fallback, User_Manual) |
| `meal_risk_tags` | `MealRecognitionRecord` | list[str] | Get enriched risk tags or empty |

---

### 1.12 `features/meals/domain/models.py`

**Purpose**: Core domain model definitions for meals.

#### Enums & Type Aliases

```python
ImageQuality = Literal["poor", "fair", "good", "unknown"]
MatchStrategy = Literal["exact_alias", "partial_alias", "fuzzy_alias", "fallback_label", "unmatched"]

class GlycemicIndexLevel(StrEnum):
    LOW = "Low (<55)"
    MEDIUM = "Medium (56-69)"
    HIGH = "High (>70)"
    UNKNOWN = "Unknown"

class PortionSize(StrEnum):
    SMALL = "Small (e.g., half bowl)"
    STANDARD = "Standard (e.g., full bowl)"
    LARGE = "Large (e.g., upsized)"
    FAMILY = "Family Share"
```

#### Core Models

| Class | Key Fields | Purpose |
|-------|-----------|---------|
| `Nutrition` | calories, carbs_g, sugar_g, protein_g, fat_g, sodium_mg, fiber_g | Legacy nutrition record |
| `MealNutritionProfile` | Same as Nutrition (defaults 0.0) | New-format nutrition with conversions |
| `Ingredient` | name, amount_g, is_hidden, allergen_info | Meal component |
| `LocalizationDetails` | dialect_name, variant, detected_components | Cultural meal nuance |
| `SafetyAnalysis` | is_safe_for_consumption, risk_factors, diabetic_warning, hypertensive_warning | Meal safety flags |
| `MealState` | dish_name, confidence_score, identification_method, ingredients, nutrition, portion_size, glycemic_index_estimate, localization, visual_anomalies, suggested_modifications | Legacy vision output |
| `MealEvent` | name, ingredients, nutrition, timestamp | User-logged meal |
| `MealPortionEstimate` | amount, unit, confidence | Portion specification |
| `PortionReference` | unit, grams, confidence | Food portion reference |
| `RawFoodSourceRecord` | source_name, source_id, source_path | Food source provenance |
| `PerceivedMealItem` | label, candidate_aliases, detected_components, portion_estimate, preparation, confidence | Detected meal item |
| `MealPerception` | meal_detected, items, uncertainties, image_quality, confidence_score | Vision perception aggregate |
| `NormalizedMealItem` | detected_label, canonical_food_id, canonical_name, matched_alias, match_strategy, match_confidence, preparation, portion_estimate, estimated_grams, nutrition, risk_tags, source_dataset | Normalized food item |
| `EnrichedMealEvent` | meal_name, normalized_items, total_nutrition, risk_tags, unresolved_items, source_records, needs_manual_review, summary | Enriched meal event |
| `VisionResult` | primary_state, perception, enriched_event, raw_ai_output, needs_manual_review, processing_latency_ms, model_version | Vision pipeline result |
| `ImageInput` | source, filename, mime_type, content, metadata | Upload image payload |
| `DietaryClaim` | label, confidence | User-claimed food |
| `DietaryClaims` | claimed_items, consumption_fraction, meal_time_label, vendor_or_source, preparation_override, dietary_constraints, goal_context, certainty_level, ambiguity_notes | Aggregated claims |
| `ContextSnapshot` | timestamp, meal_window, location_cluster, vendor_candidates, regional_food_prior, user_context_snapshot | Session context |
| `RawObservationBundle` | observation_id, user_id, captured_at, source, vision_result, dietary_claims, context, image_quality, confidence_score, unresolved_conflicts | Complete observation |
| `ValidatedMealEvent` | event_id, user_id, captured_at, meal_name, consumption_fraction, canonical_items, alternatives, confidence_summary, provenance, needs_manual_review | Validated meal for persistence |
| `NutritionRiskProfile` | profile_id, event_id, user_id, captured_at, calories, carbs_g, sugar_g, protein_g, fat_g, sodium_mg, fiber_g, risk_tags, uncertainty | Nutrition risk record |
| `MealAnalysisResult` | raw_observation, validated_event, nutrition_profile | Complete analysis result |

---

### 1.13 `features/meals/domain/nutrition_models.py`

**Purpose**: Nutrition summary domain models.

#### Classes

| Class | Fields | Purpose |
|-------|--------|---------|
| `NutritionTotals` | calories, sugar_g, sodium_mg, protein_g, fiber_g (all default 0.0) | Nutrition aggregate |
| `NutritionInsight` | code, title, summary, actions | Pattern insight recommendation |
| `DailyNutritionSummary` | date, meal_count, last_logged_at, consumed, targets, remaining, insights, recommendation_hints | Complete daily summary |

---

### 1.14 `features/meals/domain/recognition.py`

**Purpose**: Meal recognition record model.

#### Classes

| Class | Fields | Purpose |
|-------|--------|---------|
| `MealRecognitionRecord` | id, user_id, captured_at, source, meal_state, meal_perception, enriched_event, analysis_version, multi_item_count | Persistent meal record |

---

### 1.15 `features/meals/domain/weekly_summary.py`

**Purpose**: Weekly nutrition summary calculations.

#### Functions

| Function | Signature | Returns | Purpose |
|----------|-----------|---------|---------|
| `build_weekly_nutrition_summary` | `(meal_history, week_start, timezone_name)` | dict | Generate weekly report with daily breakdown |
| `_week_end` | `(week_start)` | date | Calculate week end (start + 6 days) |

#### Pattern Flags Generated
- `repetitive_meals`: Dish repeat ≥ 3 times
- `high_weekly_sodium`: > 14,000 mg
- `high_weekly_sugar`: > 210 g

---

## 2. PROFILES FEATURE

### 2.1 Module Overview
The profiles feature provides:
- Health profile management
- Onboarding workflows
- Profile completeness tracking
- Role-based permissions
- Community features

---

### 2.2 `features/profiles/use_cases.py`

**Purpose**: Health profile and onboarding orchestration.

#### Functions

| Function | Signature | Returns | Purpose |
|----------|-----------|---------|---------|
| `to_profile_response` | `(profile, fallback_mode)` | `HealthProfileResponseItem` | Project domain profile to API response |
| `_to_onboarding_response` | `(state, profile)` | `HealthProfileOnboardingEnvelopeResponse` | Project onboarding state + profile |
| `get_profile` | `(context, session)` | `HealthProfileEnvelopeResponse` | Fetch or initialize user's health profile |
| `patch_profile` | `(context, session, payload)` | `HealthProfileEnvelopeResponse` | Apply partial profile update |
| `get_profile_onboarding` | `(context, session)` | `HealthProfileOnboardingEnvelopeResponse` | Get onboarding progress & profile state |
| `patch_profile_onboarding` | `(context, session, payload)` | `HealthProfileOnboardingEnvelopeResponse` | Update onboarding step with profile changes |
| `complete_profile_onboarding` | `(context, session)` | `HealthProfileOnboardingEnvelopeResponse` | Mark onboarding complete |
| `get_daily_suggestions` | `(context, session)` | `DailySuggestionsResponse` | Generate meal suggestions from profile & history |

---

### 2.3 `features/profiles/schemas.py`

**Purpose**: Pydantic schemas for profile API responses.

#### Classes

| Class | Key Fields | Purpose |
|-------|-----------|---------|
| `HealthProfileCondition` | name, severity | Medical condition record |
| `HealthProfileMedication` | name, dosage, contraindications | Medication record |
| `HealthProfileCompletenessResponse` | state (needs_profile/partial/ready), missing_fields | Profile readiness indicator |
| `HealthProfileResponseItem` | age, height_cm, weight_kg, bmi, daily_sodium_limit_mg, daily_sugar_limit_g, daily_protein_target_g, daily_fiber_target_g, target_calories_per_day, macro_focus, conditions, medications, allergies, nutrition_goals, preferred_cuisines, disliked_ingredients, budget_tier, meal_schedule, preferred_notification_channel, fallback_mode, completeness, updated_at | Complete user profile |

---

### 2.4 `features/profiles/domain/health_profile.py`

**Purpose**: Health profile domain rules and repository protocol.

#### Constants
- `DEFAULT_PROFILE_AGE = 68`

#### Protocols

```python
class HealthProfileRepository(Protocol):
    def get_health_profile(self, user_id: str) -> HealthProfileRecord | None: ...
    def save_health_profile(self, profile: HealthProfileRecord) -> HealthProfileRecord: ...
```

#### Functions

| Function | Signature | Returns | Purpose |
|----------|-----------|---------|---------|
| `default_health_profile` | `(user_id)` | `HealthProfileRecord` | Create empty profile for user |
| `compute_profile_completeness` | `(profile)` | `ProfileCompleteness` | Assess profile state & missing fields |
| `get_or_create_health_profile` | `(repository, user_id)` | `HealthProfileRecord` | Fetch or initialize profile |
| `update_health_profile` | `(repository, user_id, updates)` | `HealthProfileRecord` | Merge and persist profile updates |
| `build_user_profile_from_health_profile` | `(session, health_profile)` | `UserProfile` | Convert health profile to runtime user profile |
| `resolve_user_profile` | `(repository, session)` | tuple[HealthProfileRecord, UserProfile] | Fetch and convert both profile forms |
| `compute_bmi` | `(profile)` | float \| None | Calculate BMI from height & weight |

#### Completeness States
- `needs_profile`: ≥ 4 missing fields (conditions, nutrition_goals, preferred_cuisines, age, locale)
- `partial`: 1-3 missing fields
- `ready`: No missing fields

---

### 2.5 `features/profiles/domain/models.py`

**Purpose**: Domain model definitions for identity and profiles.

#### Type Aliases

```python
AccountRole = Literal["member", "admin"]
ProfileMode = Literal["self", "caregiver"]
PermissionScope = Literal[
    "meal:write", "meal:read", "report:write", "report:read",
    "recommendation:generate", "reminder:write", "reminder:read",
    "alert:trigger", "alert:timeline:read", "workflow:read",
    "workflow:replay", "workflow:write", "auth:audit:read"
]
MealSlot = Literal["breakfast", "lunch", "dinner", "snack"]
```

#### Classes

| Class | Fields | Purpose |
|-------|--------|---------|
| `AccountPrincipal` | account_id, email, display_name, account_role, scopes, profile_mode, subject_user_id | Authentication principal |
| `MealScheduleWindow` | slot, start_time, end_time, timezone | Meal time window definition |
| `MedicalCondition` | name, severity | Health condition |
| `Medication` | name, dosage, contraindications | Medication record |
| `UserProfile` | id, name, age, conditions, medications, profile_mode, locale, allergies, nutrition_goals, preferred_cuisines, disliked_ingredients, budget_tier, target_calories_per_day, macro_focus, meal_schedule, preferred_notification_channel, daily_sodium_limit_mg, daily_sugar_limit_g, daily_protein_target_g, daily_fiber_target_g | Complete user profile |

#### Default MealScheduleWindow
```python
[
    MealScheduleWindow(slot="breakfast", start_time="07:00", end_time="09:00"),
    MealScheduleWindow(slot="lunch", start_time="12:00", end_time="14:00"),
    MealScheduleWindow(slot="dinner", start_time="18:00", end_time="20:00"),
]
```

---

### 2.6 `features/profiles/domain/onboarding.py`

**Purpose**: Health profile onboarding state machine and workflow.

#### Protocols

```python
class HealthProfileOnboardingRepository(HealthProfileRepository, Protocol):
    def get_health_profile_onboarding_state(self, user_id: str) -> HealthProfileOnboardingState | None: ...
    def save_health_profile_onboarding_state(self, state: HealthProfileOnboardingState) -> HealthProfileOnboardingState: ...
```

#### Onboarding Steps

| Step ID | Title | Fields |
|---------|-------|--------|
| `basic_identity` | Basic Identity | age, locale, height_cm, weight_kg |
| `health_context` | Health Context | conditions, medications |
| `nutrition_targets` | Nutrition Targets | daily_sodium_limit_mg, daily_sugar_limit_g, daily_protein_target_g, daily_fiber_target_g, target_calories_per_day, macro_focus, nutrition_goals |
| `preferences` | Preferences | preferred_cuisines, allergies, disliked_ingredients, budget_tier |
| `review` | Review | (no fields) |

#### Functions

| Function | Signature | Returns | Purpose |
|----------|-----------|---------|---------|
| `list_onboarding_steps` | `()` | list[HealthProfileOnboardingStepDefinition] | Get step definitions |
| `default_health_profile_onboarding_state` | `(user_id)` | `HealthProfileOnboardingState` | Create new onboarding state |
| `get_or_create_health_profile_onboarding_state` | `(repository, user_id)` | `HealthProfileOnboardingState` | Fetch or initialize |
| `update_health_profile_onboarding` | `(repository, user_id, step_id, profile_updates)` | tuple[HealthProfileOnboardingState, HealthProfileRecord] | Progress onboarding step |
| `complete_health_profile_onboarding` | `(repository, user_id)` | tuple[HealthProfileOnboardingState, HealthProfileRecord] | Mark complete |
| `_next_onboarding_step` | `(step_id, completed_steps)` | str | Determine next incomplete step |

---

### 2.7 `features/profiles/domain/profile_tools.py`

**Purpose**: Profile tool state models for agent contexts.

#### Classes

| Class | Fields | Purpose |
|-------|--------|---------|
| `SelfToolState` | recent_meal_names, after_meal_reminder_due, meal_confirmation_rate | Self-care tool state |
| `CaregiverToolState` | high_risk_alert_count, manual_review_count, alerts | Caregiver tool state |
| `ClinicalSummaryToolState` | biomarker_summary, narrative, export_payload | Clinical export state |

---

### 2.8 `features/profiles/domain/role_tools.py`

**Purpose**: Role-based tool authorization contracts.

#### Classes

| Class | Fields | Purpose |
|-------|--------|---------|
| `RoleToolContract` | role, allowed_tools, blocked_tools, notes | Tool permissions for role |
| `AgentRoleToolContract` | agent_id, contracts | Agent tool authorization |

---

### 2.9 `features/profiles/domain/social.py`

**Purpose**: Community and social challenge models.

#### Classes

| Class | Fields | Purpose |
|-------|--------|---------|
| `BlockScore` | block_id, postal_code_prefix, sugar_reduction_points, sodium_reduction_points, active_residents | Community block score |
| `CommunityChallenge` | id, name, description, participating_blocks, leaderboard | Community challenge definition |

---

## 3. MEDICATIONS FEATURE

### 3.1 Module Overview
The medications feature provides:
- Medication regimen management
- Adherence event tracking
- Daily medication reminders
- Mobility reminder scheduling
- Adherence metrics and reporting

---

### 3.2 `features/medications/use_cases.py`

**Purpose**: Medication regimen and adherence orchestration.

#### Functions

| Function | Signature | Returns | Purpose |
|----------|-----------|---------|---------|
| `list_regimens_for_session` | `(context, user_id)` | `MedicationRegimenListResponse` | List all medication regimens |
| `create_regimen_for_session` | `(context, user_id, payload)` | `MedicationRegimenEnvelopeResponse` | Create new regimen |
| `patch_regimen_for_session` | `(context, user_id, regimen_id, payload)` | `MedicationRegimenEnvelopeResponse` | Update regimen |
| `delete_regimen_for_session` | `(context, user_id, regimen_id)` | `MedicationRegimenDeleteResponse` | Delete regimen |
| `record_adherence_for_session` | `(context, user_id, payload)` | `MedicationAdherenceEventEnvelopeResponse` | Record adherence event (taken/missed/skipped) |
| `adherence_metrics_for_session` | `(context, user_id, from_date, to_date)` | `MedicationAdherenceMetricsResponse` | Calculate adherence metrics |
| `_parse_hhmm` | `(value)` | str \| None | Validate and format HH:MM time |
| `_to_regimen_response` | `(regimen)` | `MedicationRegimenResponse` | Convert model to API response |
| `_to_adherence_response` | `(event)` | `MedicationAdherenceEventResponse` | Convert model to API response |

---

### 3.3 `features/medications/domain/medication_scheduling.py`

**Purpose**: Medication reminder generation and meal confirmation tracking.

#### Constants
- `ASIA_SINGAPORE = "+08:00"`

#### Protocols

```python
class ReminderEventRepository(Protocol):
    def get_reminder_event(self, event_id: str) -> ReminderEvent | None: ...
    def save_reminder_event(self, event: ReminderEvent) -> None: ...
```

#### Functions

| Function | Signature | Returns | Purpose |
|----------|-----------|---------|---------|
| `generate_daily_reminders` | `(user, regimens, target_date)` | list[ReminderEvent] | Generate reminders for day based on regimens |
| `mark_meal_confirmation` | `(event_id, confirmed, confirmed_at, repository)` | `ReminderEvent` | Update reminder with meal confirmation status |
| `compute_mcr` | `(events)` | `EngagementMetrics` | Calculate meal confirmation rate |
| `_parse_hhmm` | `(value)` | time | Parse HH:MM string |
| `_at` | `(d, hhmm)` | datetime | Combine date and time |
| `_find_slot_window` | `(user, slot)` | MealScheduleWindow \| None | Find meal schedule window |

#### Timing Types
- **fixed_time**: Reminder at exact time (requires `fixed_time` in HH:MM)
- **pre_meal**: Reminder before meal window start (offset_minutes before)
- **post_meal**: Reminder after meal window end (offset_minutes after)

#### Reminder Generation Logic
For each active regimen:
1. If fixed_time: Generate at specified time
2. Else for each slot in slot_scope:
   - Find user's meal window for slot
   - Calculate scheduled time based on timing_type & offset
   - Generate reminder

---

### 3.4 `features/medications/domain/mobility_scheduling.py`

**Purpose**: Mobility reminder generation.

#### Functions

| Function | Signature | Returns | Purpose |
|----------|-----------|---------|---------|
| `default_mobility_settings` | `(user_id)` | `MobilityReminderSettings` | Create default mobility settings |
| `parse_hhmm` | `(value)` | time | Parse HH:MM |
| `generate_mobility_reminders` | `(user_id, target_date, settings)` | list[ReminderEvent] | Generate mobility reminders for day |

#### Reminder Generation Logic
If enabled, generate reminders at interval_minutes from active_start_time to active_end_time.

---

## 4. SYMPTOMS FEATURE

### 4.1 Module Overview
The symptoms feature provides:
- Symptom check-in recording
- Symptom safety evaluation
- Symptom tracking and summarization

---

### 4.2 `features/symptoms/use_cases.py`

**Purpose**: Symptom check-in orchestration.

#### Functions

| Function | Signature | Returns | Purpose |
|----------|-----------|---------|---------|
| `create_checkin_for_session` | `(context, user_id, payload)` | `SymptomCheckInEnvelopeResponse` | Create symptom check-in with safety evaluation |
| `list_checkins_for_session` | `(context, user_id, from_date, to_date, limit)` | `SymptomCheckInListResponse` | List check-ins in date range (limit 1000) |
| `summarize_checkins_for_session` | `(context, user_id, from_date, to_date)` | `SymptomSummaryResponse` | Generate summary (top 5 symptoms, red flag count, severity) |
| `_to_response` | `(item)` | `SymptomCheckInResponse` | Convert model to API response |

#### Symptom Safety Evaluation
Uses `evaluate_text_safety()` to assess:
- Safety decision (accept/redact/escalate)
- Risk reasons
- Required actions
- Text redactions

#### Summary Metrics
- `total_count`: Total check-ins
- `average_severity`: Mean severity score
- `red_flag_count`: Check-ins with escalate decision
- `top_symptoms`: Top 5 symptom codes by frequency
- `latest_recorded_at`: Most recent check-in timestamp

---

## 5. ARCHITECTURE PATTERNS

### 5.1 Dependency Injection
All features use `@dataclass(frozen=True)` dependency containers:
```python
@dataclass(frozen=True)
class MealDeps:
    settings: Settings
    stores: AppStores
    coordinator: WorkflowCoordinator
```

### 5.2 Repository Protocol Pattern
Domain logic uses protocols for repository abstraction:
```python
class HealthProfileRepository(Protocol):
    def get_health_profile(self, user_id: str) -> HealthProfileRecord | None: ...
    def save_health_profile(self, profile: HealthProfileRecord) -> HealthProfileRecord: ...
```

### 5.3 State Machine Pattern
Onboarding uses state transitions:
```python
current_step → next_incomplete_step OR "review" (if complete)
```

### 5.4 Request-Response Pattern
All API operations follow:
- Input request model (Pydantic BaseModel)
- Business logic in use_cases module
- Output response model
- Error handling with `build_api_error()`

### 5.5 Normalization Pipeline
Meal analysis follows staged normalization:
1. Vision analysis → MealState
2. Perception extraction → MealPerception
3. Food store matching → NormalizedMealItem
4. Nutrition aggregation → EnrichedMealEvent
5. Risk profiling → NutritionRiskProfile

---

## 6. KEY CONSTANTS & DEFAULTS

### Meal Portion Heuristics
```python
_UNIT_GRAMS = {
    "bowl": 400.0, "cup": 250.0, "glass": 250.0, "ml": 1.0,
    "piece": 120.0, "plate": 350.0, "portion": 300.0,
    "serving": 300.0, "set": 450.0
}
```

### Profile Defaults
- `DEFAULT_PROFILE_AGE = 68`
- `daily_sodium_limit_mg = 2000.0`
- `daily_sugar_limit_g = 30.0`
- `daily_protein_target_g = 60.0`
- `daily_fiber_target_g = 25.0`

### Nutrition Summary Thresholds
| Metric | Threshold | Purpose |
|--------|-----------|---------|
| Protein avg | < 18g | Identify low protein |
| Protein dense | < 40% | Meals ≥ 20g protein |
| Fiber avg | < 5g | Identify low fiber |
| Sodium avg | > 90% daily limit | Identify high sodium |
| Sodium meals | ≥ 3 meals > 900mg | Cumulative sodium |
| Sugar avg | > 90% daily limit | Identify high sugar |
| Calories avg | > 110% target | Identify high calorie |
| Meal repeats | ≥ 3 in 7 days | Identify repetitive pattern |

---

## 7. ERROR HANDLING

All features use `build_api_error()` for consistent error responses:

```python
build_api_error(
    status_code=400,
    code="feature.error_code",
    message="Human readable message",
    details={"key": "value"}  # Optional
)
```

### Common Error Codes

**Meals**:
- `meal.upload_too_large`
- `meal.empty_upload`
- `meal.unsupported_image_format`
- `meal.duplicate_capture`
- `meal.agent_failed`
- `meal.analysis_failed`
- `meal.invalid_cursor`
- `llm.timeout`

**Profiles**:
- `profile.no_changes_requested`
- `profile.onboarding.invalid_step`

**Medications**:
- `medications.invalid_fixed_time`
- `medications.not_found`
- `medications.no_changes`

---

## 8. EXPORT SUMMARY

### Core Exports by Module

| Module | Key Exports |
|--------|------------|
| `meals/api_service.py` | analyze_meal, get_daily_summary, get_weekly_summary, list_meal_records |
| `meals/use_cases.py` | normalize_vision_result, build_meal_record |
| `meals/presenter.py` | build_meal_analysis_output |
| `profiles/use_cases.py` | get_profile, patch_profile, get_profile_onboarding, patch_profile_onboarding, complete_profile_onboarding, get_daily_suggestions |
| `profiles/domain/health_profile.py` | get_or_create_health_profile, compute_profile_completeness, compute_bmi, update_health_profile, resolve_user_profile |
| `profiles/domain/onboarding.py` | get_or_create_health_profile_onboarding_state, update_health_profile_onboarding, complete_health_profile_onboarding |
| `medications/use_cases.py` | list_regimens_for_session, create_regimen_for_session, patch_regimen_for_session, delete_regimen_for_session, record_adherence_for_session, adherence_metrics_for_session |
| `medications/domain/medication_scheduling.py` | generate_daily_reminders, mark_meal_confirmation, compute_mcr |
| `medications/domain/mobility_scheduling.py` | generate_mobility_reminders, default_mobility_settings |
| `symptoms/use_cases.py` | create_checkin_for_session, list_checkins_for_session, summarize_checkins_for_session |

---

**Documentation Generated**: Complete module reference for dietary_guardian features.
