# Dietary Guardian Companion Feature - Comprehensive Module Reference

## Overview

The Companion feature is the orchestration layer for patient-facing interactions, synthesizing clinical context, personalization, engagement assessment, and evidence-based guidance into adaptive care plans. It coordinates across health metrics, emotional state, meal patterns, medication adherence, and clinician-visible insights.

---

## 1. Core Entry Point & Orchestration

### `features/companion/service.py`

**Purpose:** Public API entrypoint for the companion feature. Provides a minimal, focused interface for building companion runtime state and executing interactions.

| Symbol | Type | Signature/Details |
|--------|------|-------------------|
| `CompanionRuntimeState` | Class | Imported from `core.use_cases`. Frozen dataclass with: `snapshot`, `personalization`, `engagement` |
| `CompanionStateInputs` | Class | Imported from `core.use_cases`. Input data aggregator for interactions |
| `build_companion_today_bundle()` | Function | Builds complete interaction result using a synthetic check-in |
| `build_companion_runtime_state()` | Function | Constructs the runtime state from inputs and interaction type |
| `run_companion_interaction()` | Function | Executes full interaction pipeline (snapshot → personalization → engagement → care plan → safety → digest → impact) |

**Relationships:**
- Gateway to all `core.use_cases` functions
- Coordinates evidence retrieval, care planning, and safety review
- Used by API endpoints for session-scoped companion operations

---

## 2. Core Domain Models

### `features/companion/core/domain/models.py`

**Purpose:** Defines all data structures used across the companion system: snapshots, contexts, assessments, and result bundles.

#### Type Aliases
| Name | Type | Values |
|------|------|--------|
| `RiskLevel` | Literal | `"low"`, `"medium"`, `"high"` |
| `EngagementMode` | Literal | `"supportive"`, `"accountability"`, `"follow_up"`, `"escalate"` |
| `UrgencyLevel` | Literal | `"routine"`, `"soon"`, `"prompt"` |
| `InteractionType` | Literal | `"chat"`, `"meal_review"`, `"check_in"`, `"report_follow_up"`, `"adherence_follow_up"` |
| `PolicyStatus` | Literal | `"approved"`, `"adjusted"`, `"escalate"` |
| `DigestPriority` | Literal | `"routine"`, `"watch"`, `"urgent"` |
| `InteractionGoal` | Literal | `"education"`, `"next_step"`, `"swap"`, `"recovery"`, `"monitoring"` |

#### Core Classes

| Class | Purpose | Key Fields |
|-------|---------|-----------|
| **CaseSnapshot** | Current longitudinal patient state | `user_id`, `profile_name`, `conditions`, `medications`, `meal_count`, `latest_meal_name`, `meal_risk_streak`, `reminder_count`, `reminder_response_rate`, `adherence_events`, `adherence_rate`, `symptom_count`, `average_symptom_severity`, `biomarker_summary` (dict), `active_risk_flags`, `generated_at` |
| **PersonalizationContext** | Guidance customization parameters | `focus_areas`, `barrier_hints`, `preferred_tone`, `cultural_context`, `emotion_signal`, `interaction_goal`, `recommended_explanation_style`, `candidate_intervention_modes` |
| **EngagementAssessment** | Risk and engagement recommendation | `risk_level`, `recommended_mode`, `rationale`, `intervention_opportunities` |
| **EvidenceCitation** | Single evidence source reference | `title`, `summary`, `source_type`, `relevance`, `confidence` |
| **EvidenceBundle** | Query results + citations | `query`, `guidance_summary`, `citations` |
| **SafetyDecision** | Policy review outcome | `policy_status`, `clinician_follow_up`, `reasons` |
| **CarePlan** | Interaction response plan | `interaction_type`, `headline`, `summary`, `reasoning_summary`, `why_now`, `recommended_actions`, `clinician_follow_up`, `urgency`, `citations`, `policy_status` |
| **ClinicianDigest** | Clinician-facing event summary | `summary`, `what_changed`, `why_now`, `time_window`, `priority`, `recommended_actions`, `interventions_attempted`, `citations`, `risk_level` |
| **ImpactSummary** | Tracked metrics and improvement signals | `baseline_window`, `comparison_window`, `tracked_metrics`, `deltas`, `intervention_opportunities`, `interventions_measured`, `improvement_signals` |
| **CompanionInteraction** | User request container | `interaction_type`, `message`, `request_id`, `correlation_id`, `emotion_signal` |
| **CompanionInteractionResult** | Complete interaction output | All seven components above |

---

## 3. Evidence Retrieval

### `features/companion/core/evidence/ports.py`

**Purpose:** Abstract interface for evidence retrieval implementations.

| Symbol | Type | Signature |
|--------|------|-----------|
| `EvidenceRetrievalPort` | Protocol | `search_evidence(*, interaction_type, message, snapshot, personalization) -> EvidenceBundle` |

### `features/companion/core/evidence/use_cases.py`

**Purpose:** Evidence application logic; delegates to port implementations.

| Function | Parameters | Returns |
|----------|-----------|---------|
| `retrieve_supporting_evidence()` | `retriever`, `interaction_type`, `message`, `snapshot`, `personalization` | `EvidenceBundle` |

**Behavior:** Wrapper that calls `retriever.search_evidence()` with all context, filtering guidance by personalization and case state.

---

## 4. Case Snapshot Building

### `features/companion/core/snapshot.py`

**Purpose:** Aggregates user data into a comprehensive longitudinal snapshot. Computes derived metrics like meal risk streaks, adherence rates, and active risk flags.

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `_meal_is_risky()` | `record: MealRecognitionRecord` | `bool` | Flags meals with high sodium (≥900mg), sugar (≥18g), calories (≥700), or low confidence/manual ID |
| `_meal_risk_streak()` | `meals: list[MealRecognitionRecord]` | `int` | Counts consecutive risky meals from most recent |
| `_adherence_rate()` | `events: list[MedicationAdherenceEvent]` | `float \| None` | Fraction of "taken" events (rounded to 4 decimals) |
| `_reminder_response_rate()` | `reminders: list[ReminderEvent]` | `float` | Fraction with meal confirmation answer |
| `_average_symptom_severity()` | `symptoms: list[SymptomCheckIn]` | `float` | Mean severity (1–5 scale, 4 decimals) |
| **`build_case_snapshot()`** | `user_profile`, `health_profile`, `meals`, `reminders`, `adherence_events`, `symptoms`, `biomarker_readings`, `clinical_snapshot` | `CaseSnapshot` | **Main function**: Aggregates all sources into single snapshot; adds risk flags for escalation, low adherence, no reminder response |

**Risk Flag Logic:**
- Adds `"symptom_escalation"` if any symptom has `safety.decision == "escalate"`
- Adds `"low_adherence"` if adherence rate < 0.7
- Adds `"no_reminder_response"` if reminders exist but response rate = 0.0

---

## 5. Engagement Assessment

### `features/companion/engagement/engagement.py`

**Purpose:** Scores near-term patient engagement risk based on clinical flags, behavioral data, and emotional signals.

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| **`assess_engagement()`** | `snapshot`, `emotion_signal` | `EngagementAssessment` | Computes risk level, recommended intervention mode, rationale, and opportunity count |

**Scoring Logic:**
- `+2` for active high-risk clinical flags (`high_hba1c`, `high_ldl`, `high_bp`, `symptom_escalation`)
- `+1` for meal risk streak ≥ 1
- `+1` for reminders unconfirmed
- `+1` for adherence rate < 0.7
- `+1` for average symptom severity ≥ 4.0
- `+1` for negative emotions (`sad`, `frustrated`, `anxious`)

**Risk Level:** 
- `"high"` if score ≥ 4
- `"medium"` if score ≥ 2
- `"low"` otherwise

**Recommended Mode:**
- `"escalate"` if symptom escalation flag
- `"supportive"` if negative emotion
- `"accountability"` if reminder unconfirmed
- `"follow_up"` if medium risk
- `"supportive"` (default)

---

## 6. Emotion Inference (Engagement Module)

### `features/companion/engagement/emotion/ports.py`

**Purpose:** Abstract emotion inference implementation.

| Type | Fields/Signature |
|------|------------------|
| **`TextEmotionInput`** | `text: str`, `language: str \| None` |
| **`SpeechEmotionInput`** | `audio_bytes: bytes`, `filename: str \| None`, `content_type: str \| None`, `transcription: str \| None`, `language: str \| None` |
| **`EmotionInferencePort`** (Protocol) | `infer_text(TextEmotionInput) -> EmotionInferenceResult`; `infer_speech(SpeechEmotionInput) -> EmotionInferenceResult`; `health() -> EmotionRuntimeHealth` |

### `features/companion/engagement/emotion/use_cases.py`

**Purpose:** Timeout-wrapped emotion inference application logic.

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `infer_text_emotion()` | `port`, `payload: TextEmotionInput`, `timeout_seconds` | `EmotionInferenceResult` | Runs text inference with ThreadPoolExecutor timeout; raises `EmotionInferenceTimeoutError` on timeout |
| `infer_speech_emotion()` | `port`, `payload: SpeechEmotionInput`, `timeout_seconds` | `EmotionInferenceResult` | Runs speech inference with ThreadPoolExecutor timeout |

### `features/companion/engagement/emotion/session.py`

**Purpose:** HTTP-facing emotion session logic; maps inference exceptions to API errors.

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `infer_text_for_session()` | `deps: EmotionDeps`, `payload: EmotionTextRequest`, `request_id`, `correlation_id` | `EmotionInferenceResponse` | Calls agent, catches errors, returns observation with request IDs |
| `infer_speech_for_session()` | `deps`, `audio_bytes`, `filename`, `content_type`, `transcription`, `language`, `request_id`, `correlation_id` | `EmotionInferenceResponse` | Calls agent for speech, handles timeout/disabled errors |
| `get_emotion_health()` | `deps` | `EmotionHealthResponse` | Returns agent runtime health status |

**Error Mapping:**
- `EmotionAgentDisabledError` → 503 (emotions.disabled)
- `EmotionSpeechDisabledError` → 503 (emotions.speech_disabled)
- Timeout error → 504 (emotions.timeout)
- `ValueError` → 400 (emotions.invalid_input)

---

## 7. Health Data Models

### `features/companion/core/health/models.py`

**Purpose:** Domain models for health profiles, clinical metrics, symptoms, medication adherence, and biomarkers.

| Class | Purpose | Key Fields |
|-------|---------|-----------|
| **HealthProfileOnboardingStepDefinition** | Onboarding flow definition | `id`, `title`, `description`, `fields` |
| **HealthProfileOnboardingState** | User onboarding progress | `user_id`, `current_step`, `completed_steps`, `is_complete`, `updated_at` |
| **MetricPoint** | Single timestamped data point | `timestamp: datetime`, `value: float` |
| **MetricTrend** | Metric trend analysis | `metric: str`, `points`, `delta`, `percent_change`, `slope_per_point`, `direction` |
| **ReportInput** | Uploaded biomarker report container | `source: Literal["pdf", "pasted_text"]`, `content_bytes`, `text`, `uploaded_at` |
| **BiomarkerReading** | Single lab result | `name`, `value`, `unit`, `reference_range`, `measured_at`, `source_doc_id` |
| **ClinicalProfileSnapshot** | Biomarker + risk flag summary | `biomarkers: dict[str, float]`, `risk_flags: list[str]` |
| **SymptomSafety** | Safety decision for symptom report | `decision: str`, `reasons`, `required_actions`, `redactions` |
| **SymptomCheckIn** | Symptom report entry | `id`, `user_id`, `recorded_at`, `severity: int (1–5)`, `symptom_codes`, `free_text`, `context`, `safety` |
| **SymptomSummary** | Aggregated symptom metrics | `total_count`, `average_severity`, `red_flag_count`, `top_symptoms`, `latest_recorded_at` |
| **MedicationAdherenceEvent** | Single dose tracking | `id`, `user_id`, `regimen_id`, `reminder_id`, `status: AdherenceStatus`, `scheduled_at`, `taken_at`, `source: AdherenceSource`, `metadata`, `created_at` |
| **MedicationAdherenceMetrics** | Adherence summary | `events`, `taken`, `missed`, `skipped`, `adherence_rate` |
| **HealthProfileRecord** | User's complete health profile | `user_id`, `age`, `locale`, `height_cm`, `weight_kg`, `daily_sodium_limit_mg`, `daily_sugar_limit_g`, `daily_protein_target_g`, `daily_fiber_target_g`, `target_calories_per_day`, `macro_focus`, `conditions`, `medications`, `allergies`, `nutrition_goals`, `preferred_cuisines`, `disliked_ingredients`, `budget_tier`, `meal_schedule`, `preferred_notification_channel`, `updated_at` |

**Enums:**
- `AdherenceStatus`: `"taken"`, `"missed"`, `"skipped"`, `"unknown"`
- `AdherenceSource`: `"manual"`, `"reminder_confirm"`, `"imported"`
- `BudgetTier`: `"budget"`, `"moderate"`, `"flexible"`
- `CompletenessState`: `"needs_profile"`, `"partial"`, `"ready"`

### `features/companion/core/health/emotion.py`

**Purpose:** Models for emotion inference results and runtime health.

| Class | Purpose | Key Fields |
|-------|---------|-----------|
| **EmotionLabel** (StrEnum) | Emotion category | `HAPPY`, `SAD`, `ANGRY`, `FRUSTRATED`, `ANXIOUS`, `NEUTRAL`, `CONFUSED`, `FEARFUL` |
| **EmotionConfidenceBand** (StrEnum) | Confidence level | `HIGH`, `MEDIUM`, `LOW` |
| **EmotionEvidence** | Single evidence item | `label: EmotionLabel`, `score: float (0–1)` |
| **EmotionInferenceResult** | Full inference output | `source_type: Literal["text", "speech", "mixed"]`, `emotion`, `score`, `confidence_band`, `model_name`, `model_version`, `evidence`, `transcription`, `created_at` |
| **EmotionRuntimeHealth** | Backend status | `status: Literal["ready", "degraded"]`, `model_cache_ready`, `source_commit`, `detail` |

### `features/companion/core/health/analytics.py`

**Purpose:** Simple engagement metrics data structure.

| Class | Purpose | Fields |
|-------|---------|--------|
| **EngagementMetrics** | Reminder engagement summary | `reminders_sent: int`, `meal_confirmed_yes: int`, `meal_confirmed_no: int`, `meal_confirmation_rate: float` |

### `features/companion/core/health/clinical_card.py`

**Purpose:** Clinical note/card container.

| Class | Purpose | Key Fields |
|-------|---------|-----------|
| **ClinicalCardRecord** | SOAP-formatted clinical note | `id`, `user_id`, `created_at`, `start_date`, `end_date`, `format: ClinicalCardFormat (Literal["sectioned", "soap"])`, `sections: dict[str, str]`, `deltas: dict[str, float]`, `trends: dict[str, dict[str, object]]`, `provenance` |

---

## 8. Impact & Trend Analysis

### `features/companion/impact/domain/trend_analysis.py`

**Purpose:** Longitudinal metric aggregation and trend computation.

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `build_metric_trend()` | `metric: str`, `points: list[MetricPoint]` | `MetricTrend` | Sorts points, computes delta, percent change, slope, and direction |
| `biomarker_points()` | `readings: list[BiomarkerReading]`, `biomarker_name: str` | `list[MetricPoint]` | Filters readings by name; converts to MetricPoint with measured_at timestamp |
| `meal_calorie_points()` | `records: list[MealRecognitionRecord]` | `list[MetricPoint]` | Aggregates calories per day; returns sorted daily totals |
| `adherence_rate_points()` | `events: list[MedicationAdherenceEvent]` | `list[MetricPoint]` | Buckets events by day; computes per-day "taken/total" rate |

**Trend Calculation:**
- `delta = last - first` (rounded to 4 decimals)
- `percent_change = ((last - first) / |first|) * 100` (null if first = 0)
- `slope = (last - first) / max(point_count - 1, 1)`
- `direction`: `"increase"` (delta > 0), `"decrease"` (delta < 0), `"flat"` (delta = 0)

### `features/companion/impact/impact.py`

**Purpose:** Builds impact summary showing tracked metrics, deltas vs. targets, and improvement signals.

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| **`build_impact_summary()`** | `snapshot`, `engagement`, `interaction`, `interventions` | `ImpactSummary` | Aggregates metrics, computes target deltas, lists improvement signals |

**Tracked Metrics Included:**
- `meal_count`, `meal_risk_streak`, `reminder_count`, `reminder_response_rate`, `adherence_events`, `symptom_checkin_count`, `active_risk_flag_count`
- Conditionally: `adherence_rate` (if not None)

**Target Deltas:**
- `meal_risk_streak_vs_target`: 0.0 - streak (aim: no risky meals)
- `reminder_response_rate_vs_target`: response_rate - 0.6 (aim: 60%+)
- `symptom_severity_vs_target`: 2.0 - avg_severity (aim: mild/low)
- `adherence_rate_vs_target`: rate - 0.8 (aim: 80%+ if tracked)

**Improvement Signals:**
- `"Adherence is at or above the target threshold."` if adherence_rate ≥ 0.8
- `"Reminder response is showing engagement with follow-through."` if response_rate ≥ 0.5
- `"No active risk flags are currently present."` if no flags

### `features/companion/impact/metrics/use_cases.py`

**Purpose:** HTTP-facing metric trend reads.

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `list_metric_trends_for_session()` | `context: AppContext`, `user_id`, `metric_names: list[str]` | `MetricTrendListResponse` | Fetches biomarkers, meals, adherence; builds trends for each requested metric |

**Supported Metrics:**
- `"meal:calories"` → daily calorie sums
- `"adherence:rate"` → daily adherence rate
- `"biomarker:*"` → any named biomarker (e.g., `"biomarker:ldl"`)

---

## 9. Care Plan Composition

### `features/companion/care_plans/care_plan.py`

**Purpose:** Generates tailored care plans based on interaction type, engagement level, and personalization context.

| Function | Purpose | Parameters | Returns |
|----------|---------|-----------|---------|
| `_message_wants_why()` | Detects if user wants explanation | `message: str` | `bool` (checks for "why", "explain", "understand") |
| `_message_wants_one_step()` | Detects if user wants single step | `message: str` | `bool` (checks for "one", "simple", "realistic", "next step") |
| **`compose_care_plan()`** | **Main function**: Generates headline, summary, actions, and urgency | `interaction`, `snapshot`, `personalization`, `engagement`, `evidence` | `CarePlan` |

**Interaction Type Patterns:**

| Type | Headline | Why Now | Actions (Customized) | Reasoning |
|------|----------|---------|--------|-----------|
| **meal_review** | "Reset the next hawker meal with one realistic swap" | Repeat risk pattern at next opportunity | 1. Choose grilled/soup/less oily 2. Smaller refined-carbs, add veg 3. Log result | Meal-centric, culturally grounded |
| **adherence_follow_up** | "Protect the next medication dose with one friction-reducing step" | Missed reminders improve via tiny, immediate steps | 1. Confirm very next dose, tie to routine 2. Move medication to usage point 3. Flag if pattern persists | Barrier-focused recovery |
| **report_follow_up** | "Turn the latest report into one follow-up priority" | Abnormal biomarkers warrant clarification + escalation readiness | 1. Review flagged trend, write question 2. Use next meal/check-in carefully 3. Escalate if symptoms worsen | Biomarker-driven |
| **chat** | "Answer the current question and land on one next best action" | User explicit, so clarify + close with action | 1. One practical step today matching concern 2. Use next check-in to confirm | Honors intent, closes loop |
| **check_in** (default) | "Stabilize the current risk signals with one manageable step" | Active opportunities for follow-through + symptom awareness | 1. Single realistic action in next hours 2. Log result 3. Surface if pattern repeats | Practical, longitudinal |

**Message-Driven Trimming:**
- If `_message_wants_one_step()` → keep first action only
- Else if `_message_wants_why()` → keep first 2 actions

**Urgency Logic:**
- `"prompt"` if `engagement.risk_level == "high"`
- `"soon"` if `engagement.risk_level == "medium"`
- `"routine"` (default)

**Summary Template:**
```
"Focus areas: {focus_areas}. Use a {tone} approach grounded in {cultural_context}. {evidence_summary}"
```
If message wants "why", appends: `" Why this matters: {why_now}"`

**Clinician Follow-up:** Set to `True` if `engagement.risk_level == "high"`

---

## 10. Personalization

### `features/companion/personalization/personalization.py`

**Purpose:** Builds personalization context (tone, cultural setting, intervention modes) and tool states for multi-modal companion.

| Function | Purpose | Parameters | Returns |
|----------|---------|-----------|---------|
| `_infer_interaction_goal()` | Infers intent from message | `interaction_type`, `message` | `InteractionGoal` |
| **`build_personalization_context()`** | **Main function**: Comprehensive personalization | `interaction_type`, `message`, `user_profile`, `health_profile`, `snapshot`, `emotion_signal` | `PersonalizationContext` |
| `get_profile_sections()` | Profile modes to display | `profile_mode: ProfileMode` | `list[str]` (returns `[profile_mode]`) |
| `build_self_tool_state()` | User-facing status | `history: list[MealState]` | `SelfToolState` |
| `build_caregiver_tool_state()` | Caregiver alerts | `history: list[MealState]` | `CaregiverToolState` |
| `build_clinical_summary_tool_state()` | Clinician summary | `user`, `history`, `biomarkers` | `ClinicalSummaryToolState` |

**Interaction Goal Inference:**

| Type | Term Matches | Result |
|------|------|--------|
| **meal_review** | "swap", "replace", "instead" | `"swap"` else `"next_step"` |
| **adherence_follow_up** | — | `"recovery"` (always) |
| Any | "why", "explain", "understand" | `"education"` |
| Any | "one", "simple", "realistic", "next step" | `"next_step"` |
| — | — | `"monitoring"` (default) |

**Focus Areas Logic:**
- Adds active risk flags from snapshot
- Adds `"meal_pattern"` if meal_risk_streak ≥ 1
- Adds `"adherence"` if reminders exist
- Adds `"symptom_monitoring"` if symptoms exist

**Barrier Hints Logic:**
- `"reminder follow-through is low"` if reminders + no responses
- `"repeat risky meal choices"` if meal_risk_streak ≥ 2
- `"patient may need a more supportive tone"` if emotion is sad/frustrated/anxious/confused

**Preferred Tone:**
- `"supportive"` if emotion is sad/frustrated/anxious
- `"direct"` if reminders unconfirmed
- `"practical"` (default)

**Cultural Context:**
- Defaults to `"Singapore hawker routines"`
- If cuisines found: `"Singapore routines with preferred cuisines: {top 3}"`

**Explanation Style:**
- `"why-first"` if goal = education
- `"action-first"` if goal = swap or next_step
- `"concise"` (default)

**Candidate Intervention Modes:**
- Always includes interaction goal
- Adds `"supportive_coaching"` if negative emotion
- Adds `"friction_reduction"` if reminders unconfirmed
- Adds `"meal_swap"` if meal_risk_streak ≥ 1

**Self Tool State:** Returns recent 5 meals, sets reminder due flag if meals exist.

**Caregiver Tool State:** Flags meals for manual review (method = "User_Manual" or confidence < 0.75) and high sodium (≥ 1000mg).

**Clinical Summary Tool State:** Combines latest meal, biomarker string, and export payload for clinician.

---

## 11. Clinician Digest

### `features/companion/clinician_digest/digest.py`

**Purpose:** Generates clinician-facing event summaries with priority and intervention tracking.

| Function | Purpose | Parameters | Returns |
|----------|---------|-----------|---------|
| **`build_clinician_digest()`** | **Main function**: Synthesizes care plan into clinician brief | `interaction`, `snapshot`, `engagement`, `care_plan`, `evidence`, `safety` | `ClinicianDigest` |

**What Changed Logic:**
- Adds `"Active risk flags: {flags}."` if flags exist
- Adds `"Latest meal logged: {name}."` if meal exists
- Adds reminder response rate % if reminders logged
- Adds symptom count + avg severity if symptoms exist

**Why Now Override:**
- If `interaction_type == "report_follow_up"`: `"Abnormal report-linked biomarkers and current symptoms make this the highest-yield clinician update."`
- If `interaction_type == "adherence_follow_up"`: `"Repeated adherence friction can be addressed earlier if the clinician sees the barrier pattern now."`
- Else: uses `care_plan.why_now`

**Priority Logic:**
- `"urgent"` if `safety.policy_status == "escalate"` OR `engagement.risk_level == "high"`
- `"watch"` if `engagement.risk_level == "medium"`
- `"routine"` (default)

**Interventions Attempted:**
- Adds `"Medication reminders were generated for current regimens."` if reminders logged
- Adds `"Meal logging is active and informing current guidance."` if meals logged
- Extends with `"Companion proposed: {action}"` for top 2 care plan actions

**Summary:** `"{name} has {risk_level} near-term engagement risk. The companion is prioritizing {top 2 actions}."`

---

## 12. Clinical Card Generation

### `features/companion/clinician_digest/clinical_cards/use_cases.py`

**Purpose:** SOAP-formatted clinical note generation and retrieval for date-windowed reports.

| Function | Purpose | Parameters | Returns |
|----------|---------|-----------|---------|
| `_parse_date()` | Parses ISO date or None | `value: str \| None` | `date \| None` |
| `_resolve_date_window()` | Resolves start/end dates; defaults to 7 days | `payload: ClinicalCardGenerateRequest` | `tuple[date, date]` |
| `_trend_json()` | Converts MetricTrend to dict | `trend: MetricTrend` | `dict[str, object]` |
| `_to_response()` | Converts ClinicalCardRecord to API response | `card: ClinicalCardRecord` | `ClinicalCardResponse` |
| **`generate_clinical_card_for_session()`** | **Main function**: Generates SOAP note for window | `deps`, `user_id`, `payload` | `ClinicalCardEnvelopeResponse` |
| `list_clinical_cards_for_session()` | Lists historical cards | `deps`, `user_id`, `limit` | `ClinicalCardListResponse` |
| `get_clinical_card_for_session()` | Retrieves specific card | `deps`, `user_id`, `card_id` | `ClinicalCardEnvelopeResponse` |

**Card Generation Logic:**

1. **Filters data by window:**
   - Meals, symptoms, adherence, biomarkers within [start_date, end_date]
   - Computes previous window (same length) for delta comparison

2. **SOAP Sections (dict):**
   - **Subjective:** Symptom check-in count + red-flag escalations
   - **Objective:** Meal count, total calories, biomarker count, adherence count
   - **Assessment:** LDL, HbA1c, adherence trends + direction/delta
   - **Plan:** Meal logging, symptom review, adherence prioritization

3. **Trends Computed:**
   - `"biomarker:ldl"`, `"biomarker:hba1c"` → via `biomarker_points()`
   - `"meal:calories"` → via `meal_calorie_points()`
   - `"adherence:rate"` → via `adherence_rate_points()`

4. **Deltas:**
   - `meal_count_delta = current_meal_count - previous_meal_count`
   - `calories_delta = current_total - previous_total`

5. **Provenance:** Records total counts of meals, symptoms, biomarkers, adherence for audit trail.

---

## 12. Core Use Cases (Main Orchestration)

### `features/companion/core/use_cases.py`

**Purpose:** Main orchestration logic; builds runtime state and executes full interaction pipeline.

| Class/Function | Type | Purpose |
|---|---|---|
| **`CompanionStateInputs`** | Frozen Dataclass | Container for all input data (user_profile, health_profile, meals, reminders, adherence, symptoms, biomarkers, clinical_snapshot, emotion_signal) |
| **`CompanionRuntimeState`** | Frozen Dataclass | Output of state-building: snapshot, personalization, engagement |
| **`build_companion_runtime_state()`** | Function | Orchestrates snapshot, personalization, and engagement assessment from inputs |
| **`run_companion_interaction()`** | Function | **Full pipeline**: state → evidence → care plan → safety review → clinician digest → impact summary → result bundle |
| **`build_companion_today_bundle()`** | Function | Creates synthetic "check-in" interaction and returns complete result tuple (snapshot, engagement, personalization, digest, impact, full_result) |

**Interaction Pipeline Flow:**

```
CompanionInteraction (user message/type)
    ↓
[build_companion_runtime_state]
    ├→ build_case_snapshot (aggregates health data)
    ├→ build_personalization_context (tailors guidance)
    └→ assess_engagement (scores risk + mode)
    ↓
[retrieve_supporting_evidence] → evidence bundle
    ↓
[compose_care_plan] → interaction response
    ↓
[review_care_plan + apply_safety_decision] → safety-gated plan
    ↓
[build_clinician_digest] → clinician event summary
    ↓
[build_impact_summary] → metrics & improvement signals
    ↓
CompanionInteractionResult (complete output)
```

**Dependencies:**
- Imports from: `care_plans`, `clinician_digest`, `engagement`, `impact`, `personalization`, `evidence`, `safety.service`, `snapshot`

---

## Relationships & Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INTERACTION (chat/meal_review/etc)     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                 ┌─────────────▼─────────────┐
                 │ build_companion_runtime   │
                 │ _state()                  │
                 └────┬────────┬────────┬────┘
                      │        │        │
        ┌─────────────┴┐  ┌───┴──────────────┐  ┌──────────────┐
        │              │  │                  │  │              │
        ▼              ▼  ▼                  ▼  ▼              ▼
    SNAPSHOT    PERSONALIZATION     ENGAGEMENT    (emotion)
    ├─meals     ├─focus_areas      ├─risk_level  └─used by
    ├─sympt     ├─barriers         ├─mode          engagement
    ├─adhere    ├─tone             └─rationale
    ├─biomark   ├─cultural_ctx
    └─flags     └─interaction_goal
    
        │            │                  │
        └────────────┼──────────────────┘
                     │
                     ▼
            ┌─────────────────────┐
            │ retrieve_supporting │
            │ evidence()          │
            └─────────┬───────────┘
                      │
                      ▼
                EVIDENCE_BUNDLE
                └─citations
    
    snapshot + personalization + engagement + evidence
                │
                ▼
        ┌──────────────────────┐
        │ compose_care_plan()  │
        └─────┬────────────────┘
              │
              ▼
          CARE_PLAN
          ├─headline
          ├─why_now
          ├─actions
          ├─urgency
          └─citations
              │
              ├──→ ┌─────────────────────┐
              │    │ review_care_plan()  │
              │    └────┬────────────────┘
              │         │
              │         ▼
              │    SAFETY_DECISION
              │    ├─policy_status
              │    ├─clinician_follow_up
              │    └─reasons
              │
              └──→ [apply_safety_decision]
              │        │
              ▼        ▼
          ┌─────────────────────┐
          │ build_clinician_    │
          │ digest()            │
          └────┬────────────────┘
               │
               ▼
          CLINICIAN_DIGEST
          ├─summary
          ├─what_changed
          ├─priority
          └─interventions_attempted
               │
               │    ┌────────────────────┐
               │    │ build_impact_sum   │
               │    │ mary()             │
               │    └────┬───────────────┘
               │         │
               │         ▼
               │    IMPACT_SUMMARY
               │    ├─tracked_metrics
               │    ├─deltas
               │    ├─improvement_signals
               │
               └─→ COMPANION_INTERACTION_RESULT
                   ├─interaction
                   ├─snapshot
                   ├─engagement
                   ├─care_plan
                   ├─clinician_digest_preview
                   ├─impact
                   ├─evidence
                   └─safety
```

---

## Module Dependency Summary

| Module | Depends On | Provides |
|--------|-----------|----------|
| **service.py** | core.use_cases | Public API (4 exports) |
| **core/domain/models.py** | (none) | 11 Pydantic models + 7 type aliases |
| **core/snapshot.py** | health.models, profiles, meals, reminders | `build_case_snapshot()` |
| **core/evidence/ports.py** | domain | `EvidenceRetrievalPort` protocol |
| **core/evidence/use_cases.py** | domain, ports | `retrieve_supporting_evidence()` |
| **engagement/engagement.py** | domain | `assess_engagement()` |
| **engagement/emotion/ports.py** | health.emotion | `EmotionInferencePort` protocol, input types |
| **engagement/emotion/use_cases.py** | emotion.ports | Timeout-wrapped inference |
| **engagement/emotion/session.py** | emotion.use_cases, agent | HTTP-facing wrapper |
| **impact/domain/trend_analysis.py** | health.models, meals | Trend computation (4 functions) |
| **impact/impact.py** | domain | `build_impact_summary()` |
| **impact/metrics/use_cases.py** | domain | HTTP session wrapper |
| **care_plans/care_plan.py** | domain, evidence | `compose_care_plan()` |
| **personalization/personalization.py** | domain, health.models, profiles | `build_personalization_context()` + 3 tool builders |
| **clinician_digest/digest.py** | domain, care_plan | `build_clinician_digest()` |
| **clinician_digest/clinical_cards/use_cases.py** | health.clinical_card, impact.domain | Card generation + retrieval (3 functions) |
| **core/use_cases.py** | All of above + safety.service | `build_companion_runtime_state()`, `run_companion_interaction()`, `build_companion_today_bundle()` |

---

## Key Design Patterns

1. **Port-Based Abstraction:** Evidence retrieval and emotion inference use Protocol-based ports for pluggable implementations.

2. **Dataclass Freezing:** `CompanionStateInputs` and `CompanionRuntimeState` are frozen dataclasses for immutability and hashing safety.

3. **Composition over Inheritance:** All output types are Pydantic BaseModels; complex flows use function composition.

4. **Scoring & Thresholding:** Engagement risk, urgency, and priority use integer accumulation + threshold logic (e.g., score ≥ 4 → "high" risk).

5. **Message-Driven Adaptation:** Care plan templates and action trimming respond to user intent detection ("one step", "why").

6. **Longitudinal Aggregation:** Snapshot and trend analysis split data gathering (snapshot) from trend computation (trend_analysis), enabling reuse.

7. **Error Mapping:** Session-level wrappers catch domain exceptions and translate to HTTP status codes.

8. **Context Preservation:** `request_id` and `correlation_id` thread through emotion sessions and responses for observability.

---

## Configuration & Constants

- **Reminder response rate target:** 60% (0.6)
- **Adherence rate target:** 80% (0.8)
- **Meal sodium alert threshold:** 900mg (risk), 1000mg (caregiver alert)
- **Meal sugar alert threshold:** 18g
- **Meal calorie alert threshold:** 700
- **Meal confidence floor:** 0.75
- **Symptom severity max (high):** 4.0 / 5
- **Adherence low threshold:** 70% (0.7)
- **Emotion thresholds:** sad/frustrated/anxious trigger supportive mode

---

## Summary

The **Companion** feature is a sophisticated orchestration layer that synthesizes real-time patient data (meals, symptoms, medication adherence, biomarkers) with personalization signals (emotions, cultural context, barriers) to generate adaptive, next-step-focused care plans. It routes escalations to clinicians, tracks impact via longitudinal trends, and maintains engagement through emotion-aware messaging and culturally grounded meal guidance. All components are designed for composability and testability through protocol-based abstraction and immutable data structures.