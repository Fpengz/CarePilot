# Comprehensive Codebase Map: dietary_tools

> **Status**: Archived snapshot (pre feature-first refactor).  
> **Last Reviewed**: March 12, 2026  
> **Current reference**: `ARCHITECTURE.md` and `docs/developer-guide.md`

## PART 1: SERVICES LAYER (src/dietary_guardian/services/*)

### Core Services (39 files)

#### Nutrition & Meal Analysis
- **canonical_food_service.py** (397 lines)
  - PURPOSE: Loads and indexes canonical food database (USDA, Open Food Facts, sg_hawker_food)
  - KEY FUNCTIONS: normalize_text(), build_default_canonical_food_records(), rank_food_candidates(), find_food_by_name()
  - IMPORTS FROM: meal_catalog_service (DEFAULT_MEAL_CATALOG), infrastructure.food.ingestion
  - USED BY: agents/vision.py (_SeededFoodStore), applications/meals/use_cases.py, apps/api services/meals.py

- **meal_catalog_service.py** (158 lines)
  - PURPOSE: Defines default meal catalog for Singapore hawker cuisine
  - KEY FUNCTIONS: list_default_catalog(), find_catalog_item_by_title()
  - IMPORTS FROM: models.recommendation_agent (MealCatalogItem)
  - USED BY: canonical_food_service.py, meal_record_utils.py

- **meal_record_utils.py** (utility functions)
  - PURPOSE: Utility extractors for meal recognition records (display name, nutrition, ingredients, confidence)
  - KEY FUNCTIONS: meal_display_name(), meal_nutrition(), meal_ingredients(), meal_confidence(), meal_identification_method()
  - IMPORTS FROM: domain.meals, models.meal_record
  - USED BY: weekly_nutrition_service, daily_nutrition_service, recommendation_service, apps/api services

- **weekly_nutrition_service.py** (71 lines)
  - PURPOSE: Builds weekly nutrition summaries with daily breakdowns and pattern detection
  - KEY FUNCTIONS: build_weekly_nutrition_summary()
  - IMPORTS FROM: meal_record_utils, timezone_utils
  - USED BY: apps/api services/meals.py

- **daily_nutrition_service.py** (183 lines)
  - PURPOSE: Builds daily nutrition summaries with per-meal details and totals
  - KEY FUNCTIONS: build_daily_nutrition_summary()
  - IMPORTS FROM: meal_record_utils, models.daily_nutrition
  - USED BY: apps/api services/meals.py

#### Health Profile & Personalization
- **health_profile_service.py** (109 lines)
  - PURPOSE: Health profile CRUD, BMI calculation, profile completeness scoring
  - KEY FUNCTIONS: resolve_user_profile(), get_or_create_health_profile(), compute_bmi(), compute_profile_completeness()
  - IMPORTS FROM: models.health_profile, models.identity
  - USED BY: apps/api services (health_profiles, meals, recommendations)

- **health_profile_onboarding_service.py** (139 lines)
  - PURPOSE: Validates and normalizes health profile onboarding data
  - KEY FUNCTIONS: validate_health_profile_input(), normalize_onboarding_input()
  - IMPORTS FROM: models.health_profile_onboarding
  - USED BY: apps/api services/health_profiles.py

- **daily_suggestions_service.py** (260 lines)
  - PURPOSE: Generates personalized daily meal suggestions based on health profile & clinical data
  - KEY FUNCTIONS: build_daily_suggestions()
  - IMPORTS FROM: health_profile_service, recommendation_service, report_parser_service
  - USED BY: apps/api services/health_profiles.py

#### Recommendation & Clinical Logic
- **recommendation_service.py** (102 lines)
  - PURPOSE: Simple meal recommendations with localized hawker advice and safety validation
  - KEY FUNCTIONS: generate_recommendation()
  - IMPORTS FROM: meal_record_utils, safety.engine
  - USED BY: apps/api services/recommendations.py, applications/suggestions/use_cases.py

- **recommendation_agent_service.py** (675 lines) ⚠️ LARGEST SERVICE
  - PURPOSE: Complex recommendation agent with meal substitution, scoring, preference tracking
  - KEY FUNCTIONS: Multiple classes for preference tracking, substitution scoring, interaction handling
  - IMPORTS FROM: canonical_food_service, health_profile_service, meal_record_utils, safety.engine
  - DEPENDENCIES: RecommendationAgentRepository protocol (needs canonical_foods, preferences, interactions)
  - USED BY: apps/api services/recommendation_agent.py

- **report_parser_service.py** (84 lines)
  - PURPOSE: Parses clinical reports (biomarker readings, symptoms) into ClinicalProfileSnapshot
  - KEY FUNCTIONS: parse_report_input(), build_clinical_snapshot()
  - IMPORTS FROM: models.report
  - USED BY: apps/api services (recommendations, companion_context), applications/suggestions/use_cases.py

#### Notification & Reminder Management
- **notification_service.py** (350 lines)
  - PURPOSE: Multi-channel reminder dispatch (in-app, push, telegram, whatsapp, wechat) with outbox pattern
  - KEY FUNCTIONS: dispatch_reminder(), dispatch_reminder_async(), trigger_alert()
  - IMPORTS FROM: alerting_service, channels/*, runtime_dependencies
  - USED BY: reminder_scheduler.py, apps/api tests

- **reminder_notification_service.py** (217 lines)
  - PURPOSE: Scheduled reminder creation and notification preference management
  - KEY FUNCTIONS: dispatch_due_reminder_notifications(), create_reminder_notification()
  - IMPORTS FROM: ports (ReminderSchedulerRepository), message_composer
  - USED BY: reminder_scheduler.py

- **reminder_scheduler.py** (63 lines)
  - PURPOSE: Background job runner for periodic reminder dispatch (entry point: run_reminder_scheduler_loop)
  - KEY FUNCTIONS: run_reminder_scheduler_once(), run_reminder_scheduler_loop()
  - IMPORTS FROM: reminder_notification_service, alerting_service
  - USED BY: apps/api run_reminder_scheduler.py, apps/workers run.py

- **medication_service.py** (166 lines)
  - PURPOSE: Medication reminder scheduling and adherence tracking
  - KEY FUNCTIONS: schedule_medication_reminder(), record_medication_taken()
  - IMPORTS FROM: models.medication
  - USED BY: apps/api services/reminders.py

- **mobility_service.py** (211 lines)
  - PURPOSE: Physical activity reminders based on mobility settings
  - KEY FUNCTIONS: default_mobility_settings(), generate_mobility_reminders(), parse_hhmm()
  - IMPORTS FROM: models.medication, models.mobility
  - USED BY: apps/api services/reminders.py

#### Alerting & Outbox (Infrastructure)
- **alerting_service.py** (538 lines) ⚠️ SECOND LARGEST SERVICE
  - PURPOSE: Alert publishing, delivery result tracking, outbox worker pattern
  - KEY FUNCTIONS: AlertPublisher, OutboxWorker (async alert processing), AlertRepositoryProtocol
  - IMPORTS FROM: domain.alerts, domain.notifications, infrastructure.persistence
  - USED BY: notification_service.py, platform_tools.py, reminder_scheduler.py, runtime_dependencies.py
  - KEY NOTES: Defines AlertRepositoryProtocol - critical interface for persistence

- **message_composer.py** (53 lines)
  - PURPOSE: Formats alert messages for different channels (in-app, push, telegram, whatsapp, wechat)
  - KEY FUNCTIONS: compose_alert_message(), format_alert_text_for_transport()
  - IMPORTS FROM: models.alerting, models.contracts
  - USED BY: Not directly used (infrastructure helper)

#### Media & File Handling
- **upload_service.py** (154 lines)
  - PURPOSE: Image upload validation and downscaling
  - KEY FUNCTIONS: _maybe_downscale_image(), SUPPORTED_IMAGE_TYPES
  - IMPORTS FROM: models.meal
  - USED BY: apps/api services/meals.py

- **media_ingestion.py** (154 lines)
  - PURPOSE: Meal image capture envelope creation and duplicate detection
  - KEY FUNCTIONS: build_capture_envelope(), should_suppress_duplicate_capture()
  - IMPORTS FROM: models.contracts (CaptureEnvelope)
  - USED BY: apps/api services/meals.py

#### Utilities & Infrastructure Helpers
- **timezone_utils.py** (18 lines)
  - PURPOSE: Timezone conversion utilities
  - KEY FUNCTIONS: resolve_timezone(), local_date_for()
  - USED BY: weekly_nutrition_service, apps/api services

- **output_contracts.py** (builds presentation models from vision/clinical results)
  - PURPOSE: Converts internal models to API-friendly presentation contracts
  - USED BY: workflow_coordinator.py

- **runtime_dependencies.py** (24 lines)
  - PURPOSE: Dependency injection factory functions for repositories
  - KEY FUNCTIONS: build_runtime_store(), build_reminder_scheduler_repository(), build_alert_repository()
  - IMPORTS FROM: infrastructure.persistence, alerting_service
  - USED BY: reminder_scheduler.py, notification_service.py

#### Advanced/Complex Services
- **emotion_service.py** (139 lines)
  - PURPOSE: Bridges application emotion inference ports to inference engine
  - IMPORTS FROM: application.emotion.ports, application.emotion.use_cases
  - USED BY: apps/api deps.py

- **readiness_service.py** (211 lines)
  - PURPOSE: System readiness check (DB connection, LLM availability, storage health)
  - KEY FUNCTIONS: build_readiness_report()
  - USED BY: apps/api routers/health.py

- **dashboard_service.py** (utility aggregator)
  - PURPOSE: Aggregates engagement metrics, recommendations, reminders for dashboard views
  - USED BY: apps/api services

- **metrics_trend_service.py** (analyzes meal/medication trends over time)
  - PURPOSE: Meal frequency patterns, sodium/sugar trends, adherence metrics
  - USED BY: apps/api services/metrics.py, services/clinical_cards.py

- **social_service.py** (community challenges, block scores)
  - PURPOSE: Community engagement tracking
  - USED BY: apps/api services

#### Policy & Access Control
- **authorization.py** (scope-based access control)
  - PURPOSE: Authorization checks (has_scopes), profile mode defaults by role
  - USED BY: apps/api routes_shared.py, policy.py

- **policy_service.py** (141 lines)
  - PURPOSE: Tool policy evaluation and persistence
  - KEY FUNCTIONS: evaluate_tool_policy(), create_tool_policy_record(), apply_tool_policy_patch()
  - USED BY: apps/api services/workflows_policies.py

#### Tool & Workflow Management
- **tool_registry.py** (147 lines)
  - PURPOSE: Central tool spec registration, execution, and metrics tracking
  - KEY CLASS: ToolRegistry
  - USED BY: platform_tools.py, workflow_coordinator.py, apps/api deps.py

- **platform_tools.py** (58 lines)
  - PURPOSE: Builds tool registry with trigger_alert tool
  - KEY FUNCTION: build_platform_tool_registry()
  - IMPORTS FROM: tool_registry, alerting_service, notification_service
  - USED BY: apps/api deps.py

- **workflow_coordinator.py** (80 lines)
  - PURPOSE: Orchestrates meal analysis, alert, report parsing, and replay workflows
  - KEY CLASS: WorkflowCoordinator (run_meal_analysis_workflow, run_alert_workflow)
  - IMPORTS FROM: memory_services, tool_registry, output_contracts
  - USED BY: apps/api deps.py

#### Memory & State
- **memory_services.py** (104 lines)
  - PURPOSE: In-memory caches for profiles, clinical snapshots, event timelines
  - KEY CLASSES: ProfileMemoryService, ClinicalSnapshotMemoryService, EventTimelineService
  - USED BY: workflow_coordinator.py

#### Ports (Interface Definitions)
- **ports.py** (Protocol definitions)
  - KEY CLASSES: ReminderNotificationRepository, ReminderSchedulerRepository
  - USED BY: reminder_notification_service.py, reminder_scheduler.py, runtime_dependencies.py

### Channels Subpackage (4 files)
- **channels/base.py**: ChannelResult, base interface
- **channels/telegram.py**: TelegramChannel implementation
- **channels/whatsapp.py**: WhatsAppChannel implementation
- **channels/wechat.py**: WeChatChannel implementation
- USED BY: notification_service.py, platform_tools.py

---

## PART 2: AGENTS LAYER (src/dietary_guardian/agents/*)

### Agent Modules (5 files)

- **dietary.py** (80 lines)
  - PURPOSE: Dietary meal analysis agent wrapping LLM inference with safety checks
  - KEY FUNCTION: process_meal_request() - async meal analysis with warnings
  - KEY CLASS: AgentResponse (analysis, advice, is_safe, warnings)
  - IMPORTS FROM: config.llm (LLMCapability), agents.executor (InferenceEngine), safety.engine
  - USED BY: apps/api services/meals.py (indirectly through registry)
  - NOTE: Uses SYSTEM_PROMPT "Uncle Guardian" persona for Singaporean seniors

- **vision.py** (200+ lines)
  - PURPOSE: Meal perception and normalization - extracts dish names, portions, confidence from images
  - KEY CLASS: HawkerVisionModule
  - KEY FUNCTIONS: Image to MealPerception via LLM, _SeededFoodStore integration
  - IMPORTS FROM: canonical_food_service, application.meals (normalize_vision_result, build_meal_record), agents.executor
  - USED BY: apps/api services/meals.py
  - NOTE: Handles image fallback strategies and slow inference warnings

- **executor.py** (150+ lines)
  - PURPOSE: Inference engine that abstracts provider differences (OpenAI, Gemini, Test, Ollama, vLLM)
  - KEY CLASS: InferenceEngine, ProviderStrategy (Protocol)
  - KEY FUNCTIONS: infer() - runs pydantic-ai Agent with schema validation and retries
  - IMPORTS FROM: config.llm (LLMCapability, ModelProvider), llm (LLMFactory), models.inference
  - USED BY: agents.dietary, agents.vision, applications
  - NOTE: Handles output retries, latency logging, multi-modality support

- **registry.py**
  - PURPOSE: Agent registry for runtime composition
  - KEY FUNCTION: build_default_agent_registry()
  - USED BY: apps/api deps.py

- **__init__.py**
  - Re-exports key classes for external imports

---

## PART 3: LLM LAYER (src/dietary_guardian/llm/*)

### LLM Modules (4 files)

- **factory.py** (200+ lines)
  - PURPOSE: Factory for constructing LLM clients (OpenAI, Google Gemini, Ollama, vLLM, Test)
  - KEY CLASS: LLMFactory
  - KEY STATIC METHODS: get_model(), from_profile(), describe_model_destination()
  - IMPORTS FROM: config.llm, llm.routing (LLMCapabilityRouter), pydantic_ai
  - USED BY: agents/executor.py, agents/dietary.py, agents/vision.py
  - HANDLES: Network config (timeouts, retries), environment variable resolution, model name attachment

- **routing.py** (64 lines)
  - PURPOSE: Capability-aware routing from settings to resolved LLM runtime
  - KEY CLASS: LLMCapabilityRouter
  - KEY FUNCTION: resolve(capability) -> ResolvedModelRuntime
  - IMPORTS FROM: config.llm (LLMCapability, LLMCapabilityTarget)
  - USED BY: factory.py
  - RESOLVES: Capability → Provider → Model name, base_url, api_key

- **types.py** (24 lines)
  - PURPOSE: Shared dataclasses and re-exports for LLM infrastructure
  - KEY CLASS: ResolvedModelRuntime (frozen dataclass)
  - RE-EXPORTS: LLMCapability, ModelProvider, LocalModelProfile, LLMCapabilityTarget

- **__init__.py**
  - Re-exports LLMFactory, types, ModelType for external imports

---

## PART 4: APPLICATION LAYER (src/dietary_guardian/application/*)

### Use Case Modules (14 packages, each with use_cases.py + __init__.py + optional ports.py)

#### Core Domain Use Cases
- **meals/use_cases.py**
  - PURPOSE: Converts vision results to meal records with canonical food matching
  - KEY FUNCTIONS: build_meal_record(), normalize_vision_result()
  - IMPORTS FROM: canonical_food_service (rank_food_candidates, normalize_text)
  - DOMAIN MODEL: EnrichedMealEvent, MealNutritionProfile, NormalizedMealItem

- **care_plans/use_cases.py**
  - PURPOSE: Composes care plans from interaction, snapshot, personalization, engagement, evidence
  - KEY FUNCTION: compose_care_plan()
  - DOMAIN MODELS: CarePlan, CaseSnapshot, PersonalizationContext
  - LOGIC: Detects "why?" questions, "one step" requests, provides targeted advice

- **case_snapshot/use_cases.py**
  - PURPOSE: Aggregates user state into case snapshot (meals, medications, symptoms, risk)
  - KEY FUNCTION: build_case_snapshot()
  - IMPORTS FROM: meal_record_utils
  - DETECTS: Risky meal patterns, medication adherence, symptom severity trends

- **interactions/use_cases.py** (Orchestrator)
  - PURPOSE: Composes full care interaction response
  - KEY FUNCTION: handle_care_interaction()
  - ORCHESTRATES: case_snapshot → care_plans → clinician_digest → evidence → engagement → safety
  - IMPORTS FROM: All other application modules
  - CHOREOGRAPHY: Chains multiple use case outputs

#### Clinical & Evidence
- **evidence/use_cases.py**
  - PURPOSE: Retrieves supporting evidence (biomarkers, meal history, medication) for justification
  - KEY FUNCTION: retrieve_supporting_evidence()
  - USES: EvidenceRetrievalPort (interface)
  - RETURNS: EvidenceBundle with biomarker excerpts, meal examples, medication context

- **clinician_digest/use_cases.py**
  - PURPOSE: Produces concise clinical summary for care team
  - KEY FUNCTION: build_clinician_digest()
  - CONSUMES: CareInteraction, CaseSnapshot, EngagementAssessment, CarePlan, EvidenceBundle, SafetyDecision
  - OUTPUTS: ClinicianDigest (structured summary)

#### Personalization & Engagement
- **personalization/use_cases.py**
  - PURPOSE: Builds personalization context (preferences, cultural factors, goals)
  - KEY FUNCTION: build_personalization_context()
  - OUTPUTS: PersonalizationContext

- **engagement/use_cases.py**
  - PURPOSE: Assesses user engagement and interaction patterns
  - KEY FUNCTION: assess_engagement()
  - DETECTS: Response rates, interaction frequency, goal progress

- **impact/use_cases.py**
  - PURPOSE: Measures impact of recommendations on health metrics
  - KEY FUNCTION: build_impact_summary()
  - TRACKS: Biomarker improvements, meal quality trends, medication adherence

#### Safety & Compliance
- **safety/use_cases.py**
  - PURPOSE: Applies safety policy checks before sending recommendations
  - KEY FUNCTIONS: apply_safety_decision(), review_care_plan()
  - IMPORTS FROM: health_profile_service, safety.engine
  - BLOCKS: Contraindicated foods, unsafe medication interactions

#### Suggestions & Household
- **suggestions/use_cases.py**
  - PURPOSE: Generates meal/medication suggestions with household access control
  - KEY FUNCTION: generate_suggestions()
  - IMPORTS FROM: recommendation_service, report_parser_service, policies.household_access
  - APPLIES: Household permissions, role-based visibility

- **household/use_cases.py**
  - PURPOSE: Manages household relationships and access policies
  - IMPORTS FROM: policies.household_access (role-based permission checks)

#### Authentication & Emotion
- **auth/use_cases.py**
  - PURPOSE: Login, signup, password management
  - USES: AuthStorePort (interface)

- **emotion/use_cases.py**
  - PURPOSE: Text/speech emotion inference (delegates to inference port)
  - KEY FUNCTION: infer_text_emotion(), infer_speech_emotion()
  - USES: EmotionInferencePort (interface)
  - IMPLEMENTS: Timeout handling for inference

#### Policies
- **policies/household_access.py**
  - PURPOSE: Household access control rules (who can see what)
  - USED BY: suggestions, household modules

- **contracts/** (Presentation Models)
  - PURPOSE: Data transfer objects for API responses

---

## PART 5: DEPENDENCY ANALYSIS

### Import Flow Diagram

```
┌─────────────────────────────────────────┐
│         External Apps                    │
│  apps/api/*, apps/workers/*, tests/*   │
└────────────────┬────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │  Application   │  (Use cases orchestrate business logic)
        │  Layer         │
        └────────┬───────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌──────────┐
│Services│  │ Agents │  │   LLM    │
│        │  │        │  │          │
└────────┘  └────────┘  └──────────┘
    │            │            │
    └────────────┼────────────┘
                 │
                 ▼
        ┌────────────────┐
        │  Domain &      │
        │  Models        │
        │  Infrastructure│
        └────────────────┘
```

### Cross-Module Dependencies (Services → Services)

**HEAVY DEPENDENCIES:**
1. recommendation_agent_service → canonical_food_service (food ranking)
2. recommendation_agent_service → health_profile_service (BMI, completeness)
3. notification_service → alerting_service (publisher/worker pattern)
4. reminder_scheduler → reminder_notification_service + alerting_service
5. daily_suggestions_service → recommendation_service + report_parser_service + health_profile_service

**MEDIUM DEPENDENCIES:**
6. workflow_coordinator → memory_services + tool_registry + output_contracts
7. daily_nutrition_service → meal_record_utils
8. weekly_nutrition_service → meal_record_utils + timezone_utils

**LIGHT DEPENDENCIES (Utilities):**
9. notification_service → channels/* (transport)
10. message_composer (utility for notifications)
11. Various services → timezone_utils

### Application → Services/Agents Dependencies

**Critical Bridging:**
- **suggestions/use_cases.py** → recommendation_service, report_parser_service
- **case_snapshot/use_cases.py** → meal_record_utils
- **meals/use_cases.py** → canonical_food_service (normalize_text, rank_food_candidates)
- **emotion/use_cases.py** → application.emotion.ports (abstraction layer)

**Note:** Applications do NOT import agents directly; they remain loosely coupled through domain models.

### Agents Dependencies

All agents (dietary, vision) depend on:
- agents/executor.py (InferenceEngine)
- llm/factory.py (LLMFactory)
- config.llm (capability routing)

Vision agent additionally depends on:
- canonical_food_service.py (food ranking in _SeededFoodStore)
- application.meals (normalize_vision_result, build_meal_record)

### Apps/API Dependencies

**Most-Used Services (by frequency):**
1. health_profile_service (7 imports)
2. recommendation_agent_service (1 large import)
3. meal_record_utils (indirectly via case_snapshot)
4. emotion_service (1 import)
5. memory_services (1 import)
6. reminder_notification_service (1 import)
7. daily_nutrition_service (1 import)
8. weekly_nutrition_service (1 import)
9. medication_service (1 import)
10. mobility_service (1 import)

**Most-Used Agents/LLM:**
1. agents.vision.HawkerVisionModule (1 import)
2. llm.LLMFactory (1 import in tests)
3. agents.executor.InferenceEngine (1 import in tests)

---

## PART 6: ANALYSIS - OVERLAPS & OPPORTUNITIES

### ⚠️ OVERLAPPING RESPONSIBILITIES

1. **Recommendation Services (2 implementations)**
   - **recommendation_service.py**: Simple, stateless recommendations with localized hawker advice
   - **recommendation_agent_service.py**: Complex, stateful agent with preference tracking & substitution logic
   - **ISSUE**: recommendation_service is used by applications/suggestions, but recommendation_agent_service is used by apps/api
   - **FINDINGS**: These serve different use cases (simple vs. advanced), but naming is confusing
   - **SUGGESTION**: Consider renaming to simple_recommendation_service + preference_tracking_recommendation_agent_service

2. **Report Parsing (in 2 places)**
   - **report_parser_service.py**: parse_report_input(), build_clinical_snapshot()
   - **build_clinical_snapshot()**: Also used by applications/evidence and applications/case_snapshot indirectly
   - **STATUS**: Single source of truth, OK

3. **Meal Normalization (scattered)**
   - **agents/vision.py**: normalize_vision_result(), MealPerception → MealState
   - **application/meals/use_cases.py**: build_meal_record(), Nutrition aggregation
   - **ISSUE**: Logic split between agent and application layers
   - **SUGGESTION**: Consider moving vision normalization to application/meals/use_cases.py

4. **Daily Suggestions (multi-service)**
   - **daily_suggestions_service.py**: Orchestrates recommendation_service + report_parser_service
   - **applications/suggestions/use_cases.py**: Similar orchestration with household access control
   - **OVERLAP**: Both generate suggestions, but services version is simpler
   - **SUGGESTION**: Consolidate into application layer, remove services version

### ⚠️ RE-EXPORT CHAINS (Module A just re-exports from Module B)

1. **agents/__init__.py**
   - Re-exports: AgentResponse, dietary_agent, get_model, process_meal_request from dietary.py
   - Re-exports: InferenceEngine, destination_ref from executor.py
   - Re-exports: AgentRegistry, build_default_agent_registry from registry.py
   - Re-exports: HawkerVisionModule from vision.py
   - **STATUS**: Sensible aggregation point

2. **llm/__init__.py**
   - Re-exports: LLMFactory from factory.py
   - Re-exports: ModelType, LLMCapability, ModelProvider, LLMCapabilityTarget from types.py
   - **STATUS**: Sensible aggregation point

3. **application/__init__.py**
   - Currently minimal
   - **OPPORTUNITY**: Consider re-exporting key use case functions for cleaner API imports

### 🔍 POTENTIALLY UNUSED OR DEAD CODE

1. **dashboard_service.py** (94 lines)
   - PURPOSE: Dashboard aggregation utilities
   - USAGE: Not found in grep searches; only referenced in comments
   - **RECOMMENDATION**: Verify if actually used before removal

2. **social_service.py** (community challenges, block scores)
   - PURPOSE: Community engagement
   - USAGE: Not found in grep searches
   - **RECOMMENDATION**: Verify if actively used

3. **profile_tools_service.py** (tools for profile interactions)
   - PURPOSE: Profile-related tool definitions
   - USAGE: Not found in grep searches
   - **RECOMMENDATION**: Verify usage before cleanup

### 🎯 CONSOLIDATION OPPORTUNITIES

1. **Merge daily_suggestions_service.py into application/suggestions/use_cases.py**
   - Remove services version (260 lines)
   - Move logic to application layer (where it belongs)
   - Reduces coupling to services layer

2. **Move meal normalization logic from agents/vision.py to application/meals/use_cases.py**
   - Currently vision.py handles both perception AND normalization
   - Application should own normalization logic
   - Agent should only handle perception

3. **Consolidate recommendation services**
   - Consider whether both simple + advanced recommendation services need to coexist
   - Or create a unified recommendation service with pluggable strategies

4. **Clean up unused services**
   - Audit dashboard_service.py, social_service.py, profile_tools_service.py
   - Remove if not integrated with any apps

### 📊 SERVICE COMPLEXITY BREAKDOWN

**By Line Count:**
1. alerting_service.py (538 lines) - Alert pub/sub & outbox pattern
2. recommendation_agent_service.py (675 lines) - Complex substitution logic
3. daily_suggestions_service.py (260 lines) - Orchestrator
4. daily_nutrition_service.py (183 lines) - Aggregations
5. canonical_food_service.py (397 lines) - Food ranking algorithm
6. notification_service.py (350 lines) - Multi-channel dispatch
7. reminder_notification_service.py (217 lines) - Reminder scheduling

**Candidate for Refactor (too large):**
- recommendation_agent_service.py could be split into:
  - preference_tracking_service.py (preference snapshot operations)
  - substitution_scoring_service.py (meal alternative ranking)
  - interaction_service.py (recommendation interaction logging)

### ✅ WELL-DESIGNED PATTERNS

1. **Factory Pattern (LLMFactory)** - Excellent abstraction over multiple LLM providers
2. **Repository Pattern (ports.py)** - Clean interfaces for persistence
3. **Tool Registry** - Extensible tool registration and execution
4. **Outbox Pattern (alerting_service)** - Reliable async message delivery
5. **Channel Abstraction (channels/*)** - Pluggable notification transports

---

## PART 7: ARCHITECTURAL DECISIONS

### Current Architecture
- **Three-tier**: Services (domain helpers) → Application (use cases) → API (routers)
- **Agents**: Loosely coupled inference layer
- **LLM**: Factory-based provider abstraction

### Strengths
✅ Clear separation of concerns (services, agents, application layers)
✅ Good abstraction over LLM providers
✅ Protocol-based interfaces (Repository, Port patterns)
✅ Async/concurrent support in core services

### Weaknesses
❌ Services layer has mixed responsibilities (should be narrower)
❌ Some logic scattered across services and application (meal normalization)
❌ Large monolithic services (recommendation_agent_service)
❌ Potential unused services not being cleaned up
❌ Daily suggestions duplicated in services + application

### Recommendations
1. **Clarify service responsibilities**: Services should be stateless utilities; move stateful logic to application
2. **Move daily_suggestions_service to application layer**
3. **Refactor recommendation_agent_service** into smaller, focused services
4. **Remove or document unused services** (dashboard, social, profile_tools)
5. **Consolidate meal normalization** into application/meals
6. **Add clear documentation** for which services are "legacy" vs. "current"
