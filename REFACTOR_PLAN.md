# Refactor Plan — `src/dietary_guardian`

> Generated after a full module-by-module audit.  
> Issues are grouped by priority wave.  Each wave is independently releasable.

---

## Summary of findings

| Severity | Count | Examples |
|---|---|---|
| 🔴 Critical | 2 | God-object repository (2503 lines), untyped store wrappers |
| 🟠 High | 5 | Dead module, duplicate ports, misplaced models, bloated outbox, legacy config classes |
| 🟡 Medium | 6 | Thin shim aliases, missing docstrings, deferred-import smell, oversized files |
| 🟢 Low | 3 | Logfire import pattern, auth store duplication, thin companion services |

---

## Wave 1 — Delete dead code & fix cheap structural issues

Low risk, no behaviour change.

### 1.1 Delete `agent/shared/llm/routing_models.py`

**File:** `src/dietary_guardian/agent/shared/llm/routing_models.py`  
**Issue:** 5-line re-export shim that is **never imported anywhere** in `src/`, `apps/`, or `tests/`. Pure dead code.  
**Fix:** Delete the file.

### 1.2 Delete legacy `AppConfig` / `MedicalConfig` / `ModelSettings` / `LocalModelSettings` from `config/runtime.py`

**File:** `src/dietary_guardian/config/runtime.py`  
**Issue:** Four classes remain at the top of `runtime.py` under a `# Legacy runtime / model settings` comment.  They are only referenced by two test files (`tests/config/test_runtime_config.py`, `tests/capabilities/test_local_model_profiles.py`).  `ModelSettings` references model names (`gemini-3-flash`) that no longer map to any live provider.  `LocalModelSettings` is a thin wrapper over `LLMSettings.local.profiles` which already exists after the LLMSettings refactor.

**Fix:**
- Delete all four classes from `runtime.py`.
- Move the two corresponding test files to test the actual live equivalents (`LLMSettings.local.profiles`, `InferenceConfig`).
- Remove exports from `config/__init__.py`.

### 1.3 Remove unnecessary shim aliases `core/config/` and `core/time/`

**Files:**
- `src/dietary_guardian/core/config/__init__.py` — re-exports `AppSettings`, `get_settings` from `dietary_guardian.config`
- `src/dietary_guardian/core/time/__init__.py` — re-exports `local_date_for`, `resolve_timezone` from `dietary_guardian.shared.time`

**Issue:** These create an artificial extra hop (`core.config` → `config`, `core.time` → `shared.time`). They are not imported anywhere based on a codebase grep. Domain code should import directly from `config` or `shared.time`.  
**Fix:** Delete both shim `__init__.py` files. Delete the now-empty `core/config/` and `core/time/` directories.

### 1.4 Add missing module docstrings in `features/reminders/outbox/`

**Files missing docstrings:**
- `features/reminders/outbox/enums.py`
- `features/reminders/outbox/infra/delivery.py`
- `features/reminders/outbox/infra/knowledge.py`
- `features/reminders/outbox/infra/outbox_sqlite.py`
- `features/reminders/outbox/infra/repository.py`
- `features/reminders/outbox/models.py`
- `features/reminders/outbox/service.py`

**Fix:** Add a one-line module docstring to each file describing its purpose.

### 1.5 Consolidate `features/safety/` duplicate ports

**Issue:** Safety has two `ports.py` files with different protocols:
- `features/safety/ports.py` — `SafetyPort` (validates meals)
- `features/safety/domain/ports.py` — `DrugInteractionRepository` (DB lookup protocol)

`SafetyPort` is a public-facing application port and belongs next to `DrugInteractionRepository` in `domain/ports.py`.  
**Fix:** Move `SafetyPort` into `features/safety/domain/ports.py`. Delete `features/safety/ports.py`. Update the ~3 import sites.

### 1.6 Move `features/meals/models.py` into `features/meals/domain/`

**Issue:** `features/meals/models.py` (85 lines) contains `DietaryClaim`, `DietaryClaims`, `NutritionRiskProfile`, `RawObservationBundle`, `ValidatedMealEvent` — these are domain-layer data types that live at the feature root instead of `domain/`. The existing `features/meals/domain/models.py` is the correct home.  
**Fix:** Merge the contents of `features/meals/models.py` into `features/meals/domain/models.py`. Update all import sites (`tests/api/test_api_meal.py`, `test_api_typed_contracts.py`, `test_api_meal_weekly.py`, and the sqlite_repository).  Keep a one-line re-export shim in `features/meals/models.py` for one release cycle if preferred, then delete.

---

## Wave 2 — Split the God-object SQLite repository

**Highest-impact structural change.** No behaviour change; all tests continue to pass via `AppStores`.

### 2.1 Split `platform/persistence/sqlite_repository.py` (2503 lines, 87 methods)

**File:** `src/dietary_guardian/platform/persistence/sqlite_repository.py`  
**Issue:** A single class `SQLiteRepository` handles persistence for every domain in the application. This violates the Single Responsibility Principle and makes testing, reasoning, and future DB migrations extremely difficult.

**Proposed split** — each new file is a focused repository class sharing the same `db_path` / `Connection` pattern:

| New file | Methods moved | ~Lines |
|---|---|---|
| `sqlite_meal_repository.py` | `save_meal_record`, `list_meal_records`, `get_meal_record`, `save_meal_observation`, `list_meal_observations`, `save_validated_meal_event`, `list_validated_meal_events`, `get_validated_meal_event`, `save_nutrition_risk_profile`, `list_nutrition_risk_profiles`, `get_nutrition_risk_profile`, legacy meal record loaders | ~500 |
| `sqlite_reminder_repository.py` | `save_reminder_event`, `get_reminder_event`, `list_reminder_events`, `save_scheduled_notification`, `get_scheduled_notification`, `list_scheduled_notifications`, `lease_due_scheduled_notifications`, `mark_scheduled_notification_*`, `reschedule_scheduled_notification`, `cancel_scheduled_notifications_for_reminder`, `append_notification_log`, `replace_reminder_notification_endpoints`, `list_reminder_notification_endpoints`, `get_reminder_notification_endpoint`, `list_notification_logs`, `replace_reminder_notification_preferences`, `list_reminder_notification_preferences` | ~650 |
| `sqlite_medication_repository.py` | `save_medication_regimen`, `list_medication_regimens`, `get_medication_regimen`, `delete_medication_regimen`, `save_medication_adherence_event`, `list_medication_adherence_events`, `get_mobility_reminder_settings`, `save_mobility_reminder_settings` | ~250 |
| `sqlite_clinical_repository.py` | `save_biomarker_readings`, `list_biomarker_readings`, `save_symptom_checkin`, `list_symptom_checkins`, `save_clinical_card`, `list_clinical_cards`, `get_clinical_card`, `get_health_profile`, `save_health_profile`, `get_health_profile_onboarding_state`, `save_health_profile_onboarding_state` | ~300 |
| `sqlite_recommendation_repository.py` | `list_meal_catalog_items`, `get_meal_catalog_item`, `list_canonical_foods`, `get_canonical_food`, `find_food_by_name`, `save_recommendation`, `save_recommendation_interaction`, `list_recommendation_interactions`, `get_preference_snapshot`, `save_preference_snapshot`, `save_suggestion_record`, `list_suggestion_records`, `get_suggestion_record`, `_seed_meal_catalog`, `_seed_canonical_foods` | ~350 |
| `sqlite_alert_repository.py` | `enqueue_alert`, `lease_alert_records`, `mark_alert_delivered`, `reschedule_alert`, `mark_alert_dead_letter`, `list_alert_records` | ~250 |
| `sqlite_workflow_repository.py` | `save_tool_role_policy`, `list_tool_role_policies`, `get_tool_role_policy`, `save_workflow_contract_snapshot`, `list_workflow_contract_snapshots`, `get_workflow_contract_snapshot`, `save_workflow_timeline_event`, `list_workflow_timeline_events` | ~200 |
| `sqlite_repository.py` (keep) | `__init__`, `_init_db`, `_ensure_sqlite_column`, `close` — shared DB init + a thin facade that instantiates all sub-repos and forwards calls for backward compat during migration | ~100 |

**Migration strategy:** Keep `SQLiteRepository` as a thin composition facade delegating to the new sub-repositories. `build_app_stores()` in `domain_stores.py` continues to work unchanged. Remove the facade once all call sites are updated.

---

## Wave 3 — Replace `Any`-typed store wrappers with typed protocols

### 3.1 Replace `platform/persistence/domain_stores.py` `Any` with typed protocols

**File:** `src/dietary_guardian/platform/persistence/domain_stores.py`  
**Issue:** 86 occurrences of `Any` as the type for the underlying backend store. Every domain store class (`MealStore`, `ReminderStore`, etc.) accepts `Any` as its `_store` field, defeating type checking across the entire persistence layer.

**Fix:**
- After Wave 2, each domain store class (`MealStore`, `ReminderStore`, …) should declare its `_store` field against the corresponding typed repository protocol or concrete class (e.g., `MealStore._store: SQLiteMealRepository`).
- Alternatively, define a `Protocol` per domain (e.g., `MealRepositoryProtocol`) and annotate `_store` against it. This allows future mock injection without coupling to SQLite.
- Remove all `Any` from the file.

---

## Wave 4 — Consolidate messaging sink adapters

### 4.1 Extract concrete sinks from `platform/messaging/alert_outbox.py`

**File:** `src/dietary_guardian/platform/messaging/alert_outbox.py` (555 lines, 9 classes)  
**Issue:** The file contains the `SinkAdapter` protocol, **6 concrete delivery implementations** (InApp, Push, Email, SMS, Telegram, WhatsApp, WeChat), `AlertPublisher`, and `OutboxWorker` all in one module. The concrete adapters for Telegram, WhatsApp, and WeChat duplicate logic already present in `platform/messaging/channels/` (telegram.py, whatsapp.py, wechat.py).

**Fix:**
- Move `SinkAdapter` protocol into `platform/messaging/channels/base.py` (already exists).
- Consolidate the duplicate Telegram/WhatsApp/WeChat sink logic so each channel has one implementation — either in `channels/telegram.py` or as adapters in a thin `adapters/` sub-directory.
- Keep `OutboxWorker` and `AlertPublisher` in `alert_outbox.py` (~150 lines after extraction).
- Target: `alert_outbox.py` drops from 555 → ~150 lines.

---

## Wave 5 — Thin companion `service.py` files

### 5.1 Collapse 5-line `service.py` re-export stubs in `features/companion/`

**Issue:** Seven `service.py` files in `features/companion/` sub-packages are 5–18 lines and only re-export from the same package's `__init__` or sibling module:
- `features/companion/engagement/service.py` (5 lines)
- `features/companion/impact/service.py` (5 lines)
- `features/companion/clinician_digest/service.py` (5 lines)
- `features/companion/interactions/service.py` (5 lines)
- `features/companion/care_plans/service.py` (18 lines)
- `features/companion/personalization/service.py` (17 lines)
- `features/companion/core/service.py` (18 lines)

**Fix:** Inline the re-exports into each sub-package's `__init__.py`. Delete the redundant `service.py` stubs. The top-level `features/companion/service.py` (24 lines, the real entry point) stays as-is.

---

## Wave 6 — Address oversized domain files

### 6.1 Split `features/recommendations/domain/engine.py` (687 lines)

**Issue:** The file mixes three concerns: scoring utilities, temporal context builders, and the main orchestration entry-points.

**Proposed split:**
- `engine.py` — keeps only `generate_daily_agent_recommendation` and `build_substitution_plan` (~150 lines)
- `scoring.py` — scoring utilities and `CandidateScores` computations (~250 lines)
- `context.py` — temporal context and `SourceMealSummary` builders (~250 lines)

### 6.2 Resolve circular import / deferred import in `features/households/use_cases.py` (658 lines)

**File:** `src/dietary_guardian/features/households/use_cases.py`  
**Issue:** The file has a comment block about "deferred imports to avoid circular dependencies with the API layer." Business logic in `use_cases.py` should never depend on the API layer. This is a layer violation masquerading as a circular import.

**Fix:** Identify which types are being imported from the API layer (likely response models or request schema types). Extract those shared types into `features/households/domain/models.py` or `features/households/ports.py` so both `use_cases.py` and the router can import from the domain layer without creating a cycle.

---

## Wave 7 — Minor quality improvements

### 7.1 Guard `logfire` import in `agent/dietary/agent.py`

**File:** `src/dietary_guardian/agent/dietary/agent.py`  
**Issue:** `import logfire` + `logfire.configure(send_to_logfire=False)` at module level with `logfire_api = cast(Any, logfire)` suppresses type checking for all logfire calls. If logfire is a required dependency this cast is unnecessary; if it's optional, it should be guarded with a try/except ImportError.

**Fix:** If logfire is required, remove the cast and type the calls directly. If optional, wrap in a guard and use a no-op stub when absent.

### 7.2 `platform/persistence/contracts.py` — remove `TYPE_CHECKING`-gated alias

**File:** `src/dietary_guardian/platform/persistence/contracts.py`  
**Issue:** `AppStoreBackend` is `SQLiteAppStore` at type-check time but `Any` at runtime. This is a workaround for a circular import that should be resolved by having `domain_stores.py` accept a structural `Protocol` rather than the concrete store class.  
**Fix:** After Wave 3 (typed protocols), replace the `TYPE_CHECKING` guard with a proper protocol.

---

## Execution order

```
Wave 1 (safe deletions + cheap fixes)   ← start here, any sprint
Wave 2 (split sqlite_repository)        ← biggest impact, dedicated sprint
Wave 3 (typed store wrappers)           ← depends on Wave 2
Wave 4 (messaging consolidation)        ← independent, any sprint after Wave 1
Wave 5 (thin service stubs)             ← independent, 1–2 hours
Wave 6 (oversized domain files)         ← independent, can be done incrementally
Wave 7 (minor quality)                  ← grab-bag, any time
```

## Files NOT requiring changes

The following were reviewed and are clean:

- `core/errors.py`, `core/events.py`, `core/ids.py`, `core/types.py` — clean, minimal
- `core/contracts/agent_envelopes.py`, `core/contracts/notifications.py` — well-structured
- `agent/shared/base.py` — clean BaseAgent contract
- `agent/shared/ai/engine.py`, `agent/shared/ai/types.py` — clean after today's config refactor
- `agent/shared/llm/factory.py`, `agent/shared/llm/routing.py` — clean after today's config refactor
- `features/companion/core/domain/models.py` — well-defined canonical models
- `features/companion/core/snapshot.py` — clean pure-function snapshot builder
- `platform/scheduling/` — clean coordination + scheduler pattern
- `platform/cache/` — clean Redis/in-memory dual implementations
- `platform/auth/ports.py`, `platform/auth/session_signer.py` — clean
- `config/llm.py`, `config/app.py` — clean after today's refactor

 1. agent bases and setting designs
  2. update scripts/
  3. refactoring after merging with ervin's branch
  4. merge with xiangqi's branch