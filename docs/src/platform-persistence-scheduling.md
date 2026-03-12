# Dietary Guardian Platform Persistence Module Reference

## Overview

The persistence platform provides SQLite-based data storage with domain-specific repositories, facade classes, and bootstrap utilities. The module is organized into three main layers:
1. **Repository Layer** - Specialized SQLite repositories for different domains
2. **Store Layer** - Domain-specific facade classes wrapping repositories
3. **Bootstrap & Configuration** - Factory functions and initialization

---

## 1. `platform/persistence/__init__.py`

**Module**: Canonical exports for the persistence platform

### Exported Symbols

| Name | Type | Purpose |
|------|------|---------|
| `AlertRepositoryProtocol` | Protocol | Structural protocol for alert persistence |
| `AppStoreBackend` | TypeAlias | Backend type (SQLiteAppStore at runtime) |
| `AppStores` | Class | Aggregated domain-specific store facade |
| `CatalogRepositoryProtocol` | Protocol | Food catalog & recommendations protocol |
| `ClinicalCardRepositoryProtocol` | Protocol | Clinical card persistence protocol |
| `ClinicalRepositoryProtocol` | Protocol | Biomarkers & symptoms protocol |
| `FoodRepositoryProtocol` | Protocol | Canonical food repository protocol |
| `MealRepositoryProtocol` | Protocol | Meal records & observations protocol |
| `MedicationRepositoryProtocol` | Protocol | Medication regimens & adherence protocol |
| `ProfileRepositoryProtocol` | Protocol | Health profile persistence protocol |
| `ReminderNotificationRepository` | TypeAlias | Reminder notification persistence contract |
| `ReminderRepositoryProtocol` | Protocol | Reminders, notifications, endpoints protocol |
| `ReminderSchedulerRepository` | TypeAlias | Reminder scheduler persistence contract |
| `SQLiteAppStore` | Class | Main SQLite backend implementation |
| `SQLiteRepository` | Class | Root facade combining all repositories (deprecated) |
| `WorkflowRepositoryProtocol` | Protocol | Workflow policies & contracts protocol |
| `build_alert_repository(settings?)` | Function | Factory for alert repository |
| `build_app_store(settings)` | Function | Factory for SQLiteAppStore |
| `build_app_stores(app_store)` | Function | Factory for AppStores container |
| `build_reminder_notification_repository(settings?)` | Function | Factory for reminder notifications |
| `build_reminder_scheduler_repository(settings?)` | Function | Factory for reminder scheduler |
| `build_runtime_store(settings?)` | Function | Factory for backend store |

---

## 2. `platform/persistence/builders.py`

**Module**: Infrastructure factories for app store creation

### Public API

```python
def build_app_store(settings: Settings) -> AppStoreBackend:
    """Factory function creating SQLiteAppStore from settings."""
    return SQLiteAppStore(settings.storage.api_sqlite_db_path)
```

**Parameters:**
- `settings: Settings` - Application configuration containing database path

**Returns:**
- `AppStoreBackend` - Configured SQLite backend instance

---

## 3. `platform/persistence/contracts.py`

**Module**: Type contracts and repository exports

### Type Aliases

| Name | Value | Purpose |
|------|-------|---------|
| `AppStoreBackend` | SQLiteAppStore (runtime) | Runtime type for app store |
| `ReminderNotificationRepository` | `ServiceReminderNotificationRepository` | Re-export from core contracts |
| `ReminderSchedulerRepository` | `ServiceReminderSchedulerRepository` | Re-export from core contracts |

**Note**: Uses conditional typing to provide concrete type at runtime while maintaining generic interface during static analysis.

---

## 4. `platform/persistence/domain_stores.py`

**Module**: Domain-specific facade stores providing high-level store API

### Classes

#### `MealStore`
**Purpose**: Facade for meal-related persistence operations

**Methods**:
- `save_meal_record(record: Any) -> None` - Save meal recognition record
- `list_meal_records(user_id: str) -> list[Any]` - Get all meals for user
- `get_meal_record(user_id: str, meal_id: str) -> Any | None` - Get specific meal
- `list_meal_catalog_items(*, locale: str, slot: str | None, limit: int = 100) -> list[Any]` - Query meal catalog
- `get_meal_catalog_item(meal_id: str) -> Any | None` - Get meal catalog entry
- `save_meal_observation(observation: Any) -> None` - Save raw observation
- `list_meal_observations(user_id: str) -> list[Any]` - Get user observations
- `save_validated_meal_event(event: Any) -> None` - Save validated meal event
- `list_validated_meal_events(user_id: str) -> list[Any]` - Get validated events
- `get_validated_meal_event(user_id: str, event_id: str) -> Any | None` - Get validated event
- `save_nutrition_risk_profile(profile: Any) -> None` - Save nutrition risk assessment
- `list_nutrition_risk_profiles(user_id: str) -> list[Any]` - Get user risk profiles
- `get_nutrition_risk_profile(user_id: str, event_id: str) -> Any | None` - Get specific profile

#### `FoodStore`
**Purpose**: Facade for canonical food data

**Methods**:
- `list_canonical_foods(*, locale: str, slot: str | None, limit: int = 100) -> list[Any]` - List canonical foods
- `get_canonical_food(food_id: str) -> Any | None` - Get food by ID
- `find_food_by_name(*, locale: str, name: str) -> Any | None` - Search by name

#### `BiomarkerStore`
**Purpose**: Facade for biomarker readings

**Methods**:
- `save_biomarker_readings(user_id: str, readings: list[Any]) -> None` - Save readings
- `list_biomarker_readings(user_id: str) -> list[Any]` - Get user readings

#### `SymptomStore`
**Purpose**: Facade for symptom check-ins

**Methods**:
- `save_symptom_checkin(checkin: Any) -> Any` - Save check-in
- `list_symptom_checkins(*, user_id: str, start_at: Any | None, end_at: Any | None, limit: int = 100) -> list[Any]` - Query check-ins

#### `MedicationStore`
**Purpose**: Facade for medication regimens and adherence

**Methods**:
- `list_medication_regimens(user_id: str, *, active_only: bool = False) -> list[Any]` - Get regimens
- `save_medication_regimen(regimen: Any) -> None` - Save regimen
- `get_medication_regimen(*, user_id: str, regimen_id: str) -> Any | None` - Get specific regimen
- `delete_medication_regimen(*, user_id: str, regimen_id: str) -> bool` - Delete regimen
- `save_medication_adherence_event(event: Any) -> Any` - Record adherence
- `list_medication_adherence_events(*, user_id: str, start_at: Any | None, end_at: Any | None, limit: int = 200) -> list[Any]` - Get adherence events

#### `ReminderStore`
**Purpose**: Facade for reminders, notifications, and endpoints

**Methods** (24 total):
- `save_reminder_event(event: Any) -> None` - Save reminder event
- `get_reminder_event(event_id: str) -> Any | None` - Get reminder
- `list_reminder_events(user_id: str) -> list[Any]` - Get user reminders
- `list_reminder_notification_preferences(*, user_id: str, scope_type: str | None, scope_key: str | None, reminder_type: str | None) -> list[Any]` - Get preferences
- `replace_reminder_notification_preferences(*, user_id: str, scope_type: str | None, scope_key: str | None, preferences: list[Any]) -> list[Any]` - Replace preferences
- `list_scheduled_notifications(*, reminder_id: str | None, user_id: str | None, status: str | None, limit: int = 200) -> list[Any]` - Query notifications
- `save_scheduled_notification(notification: Any) -> Any` - Save notification
- `lease_due_scheduled_notifications(*, now: Any, limit: int = 100) -> list[Any]` - Get due notifications for processing
- `get_reminder_notification_endpoint(*, user_id: str, channel: str) -> Any | None` - Get contact endpoint
- `append_notification_log(entry: Any) -> Any` - Log notification attempt
- `cancel_scheduled_notifications_for_reminder(reminder_id: str) -> int` - Cancel all notifications for reminder
- `enqueue_alert(message: Any) -> list[Any]` - Enqueue alert message
- `list_reminder_notification_endpoints(*, user_id: str) -> list[Any]` - Get endpoints
- `replace_reminder_notification_endpoints(*, user_id: str, endpoints: list[Any]) -> list[Any]` - Replace endpoints
- `list_notification_logs(*, reminder_id: str | None, scheduled_notification_id: str | None, channel: str | None, limit: int = 200) -> list[Any]` - Get notification logs
- `get_mobility_reminder_settings(user_id: str) -> Any | None` - Get mobility settings
- `save_mobility_reminder_settings(settings: Any) -> Any` - Save mobility settings

#### `ClinicalCardStore`
**Purpose**: Facade for clinical cards

**Methods**:
- `save_clinical_card(card: Any) -> Any` - Save card
- `list_clinical_cards(*, user_id: str, limit: int = 50) -> list[Any]` - Get cards
- `get_clinical_card(*, user_id: str, card_id: str) -> Any | None` - Get specific card

#### `WorkflowStore`
**Purpose**: Facade for workflow policies and contracts

**Methods**:
- `list_tool_role_policies(*, role: str | None, agent_id: str | None, tool_name: str | None, enabled_only: bool = False) -> list[Any]` - Query policies
- `save_tool_role_policy(record: Any) -> Any` - Save policy
- `get_tool_role_policy(policy_id: str) -> Any | None` - Get policy
- `save_workflow_contract_snapshot(snapshot: Any) -> Any` - Save contract snapshot
- `list_workflow_contract_snapshots(*, limit: int = 50) -> list[Any]` - Get snapshots
- `get_workflow_contract_snapshot(*, version: int) -> Any | None` - Get snapshot by version
- `supports_contract_snapshots() -> bool` - Check if backend supports snapshots

#### `RecommendationStore`
**Purpose**: Facade for recommendations and suggestions

**Methods**:
- `save_recommendation(user_id: str, payload: dict[str, Any]) -> None` - Save recommendation
- `list_canonical_foods(*, locale: str, slot: str | None, limit: int = 100) -> list[Any]` - List foods
- `get_canonical_food(food_id: str) -> Any | None` - Get food
- `find_food_by_name(*, locale: str, name: str) -> Any | None` - Search food
- `get_meal_record(user_id: str, meal_id: str) -> Any | None` - Get meal
- `list_meal_records(user_id: str) -> list[Any]` - Get meals
- `save_biomarker_readings(user_id: str, readings: list[Any]) -> None` - Save readings
- `save_recommendation_interaction(interaction: Any) -> Any` - Log interaction
- `list_recommendation_interactions(user_id: str, *, limit: int = 200) -> list[Any]` - Get interactions
- `get_preference_snapshot(user_id: str) -> Any | None` - Get preferences
- `save_preference_snapshot(snapshot: Any) -> Any` - Save preferences
- `save_suggestion_record(user_id: str, payload: dict[str, Any]) -> dict[str, Any]` - Save suggestion
- `list_suggestion_records(user_id: str, limit: int = 20) -> list[dict[str, Any]]` - Get suggestions
- `get_suggestion_record(user_id: str, suggestion_id: str) -> dict[str, Any] | None` - Get suggestion

#### `ProfileStore`
**Purpose**: Facade for health profiles

**Methods**:
- `get_health_profile(user_id: str) -> Any | None` - Get profile
- `save_health_profile(profile: Any) -> Any` - Save profile
- `get_health_profile_onboarding_state(user_id: str) -> Any | None` - Get onboarding state
- `save_health_profile_onboarding_state(state: Any) -> Any` - Save onboarding state

#### `AlertStore`
**Purpose**: Facade for alert records

**Methods**:
- `list_alert_records(alert_id: str | None = None) -> list[Any]` - Get alert records

#### `AppStores` (Dataclass)
**Purpose**: Container aggregating all domain stores

**Attributes**:
- `meals: MealStore` - Meal store instance
- `foods: FoodStore` - Food store instance
- `biomarkers: BiomarkerStore` - Biomarker store
- `symptoms: SymptomStore` - Symptom store
- `medications: MedicationStore` - Medication store
- `reminders: ReminderStore` - Reminder store
- `clinical_cards: ClinicalCardStore` - Clinical card store
- `workflows: WorkflowStore` - Workflow store
- `recommendations: RecommendationStore` - Recommendation store
- `profiles: ProfileStore` - Profile store
- `alerts: AlertStore` - Alert store

### Functions

```python
def build_app_stores(app_store: AppStoreBackend) -> AppStores:
    """Factory creating AppStores container from backend."""
    # Returns container with all domain stores initialized
```

---

## 5. `platform/persistence/protocols.py`

**Module**: Structural protocols defining repository interfaces

### Protocols

| Protocol | Methods | Purpose |
|----------|---------|---------|
| `MealRepositoryProtocol` | 12 | Meal records, observations, validated events, nutrition profiles |
| `FoodRepositoryProtocol` | 3 | Canonical food retrieval |
| `ClinicalRepositoryProtocol` | 4 | Biomarker and symptom data |
| `MedicationRepositoryProtocol` | 6 | Medication regimens and adherence |
| `ReminderRepositoryProtocol` | 18 | Reminders, notifications, endpoints, logs, settings |
| `ClinicalCardRepositoryProtocol` | 3 | Clinical card records |
| `WorkflowRepositoryProtocol` | 6 | Tool policies and contract snapshots |
| `CatalogRepositoryProtocol` | 13 | Foods, meals, biomarkers, recommendations, preferences, suggestions |
| `ProfileRepositoryProtocol` | 4 | Health profiles and onboarding state |
| `AlertRepositoryProtocol` | 1 | Alert record listing |

**Note**: All protocols use `Protocol` class for structural typing - implementations need not inherit but must match method signatures.

---

## 6. `platform/persistence/runtime_bootstrap.py`

**Module**: Dependency factories for workers and background processes

### Functions

```python
def build_runtime_store(settings: Settings | None = None) -> AppStoreBackend:
    """Build app store instance for runtime use (workers, schedulers).
    
    Uses AppSettings.get_settings() if no settings provided.
    Returns: Configured SQLiteAppStore
    """

def build_reminder_scheduler_repository(settings: Settings | None = None) -> ReminderSchedulerRepository:
    """Factory for reminder scheduler repository.
    
    Casts runtime store to ReminderSchedulerRepository protocol.
    """

def build_reminder_notification_repository(settings: Settings | None = None) -> ReminderNotificationRepository:
    """Factory for reminder notification repository.
    
    Casts runtime store to ReminderNotificationRepository protocol.
    """

def build_alert_repository(settings: Settings | None = None) -> AlertRepositoryProtocol:
    """Factory for alert repository.
    
    Casts runtime store to AlertRepositoryProtocol.
    """
```

**Key Note**: All factories use `cast()` to provide type hints while the actual implementation is the SQLiteAppStore. This enables dependency injection outside the FastAPI context (background workers, schedulers).

---

## 7. `platform/persistence/sqlite_app_store.py`

**Module**: Main SQLite backend implementation

### Class

```python
class SQLiteAppStore(SQLiteRepository):
    """Public SQLite application store backend."""
    pass
```

**Note**: Inherits from SQLiteRepository which composes all domain-specific repositories into a single facade. This is the primary backend implementation passed to factories.

---

## 8. `platform/persistence/sqlite_bootstrap.py`

**Module**: Database schema initialization and seed data

### Schema Statements

Defines CREATE TABLE statements for 22 core tables:
- medication_regimens
- reminder_events
- meal_records
- meal_observations
- meal_validated_events
- meal_nutrition_risk_profiles
- biomarker_readings
- recommendation_records
- suggestion_records
- health_profiles
- health_profile_onboarding_states
- meal_catalog
- canonical_foods
- food_alias (for food name matching)
- portion_reference
- recommendation_interactions
- preference_snapshots
- symptom_checkins
- clinical_cards
- medication_adherence_events
- reminder_notification_preferences
- scheduled_notifications
- notification_logs
- reminder_notification_endpoints
- mobility_reminder_settings
- tool_role_policies
- workflow_contract_snapshots
- workflow_timeline_events
- alert_outbox

### Migration System

`COLUMN_MIGRATIONS: tuple[tuple[str, str, str], ...]` - Backward-compatible column additions

### Functions

```python
def bootstrap_sqlite_store(db_path: str) -> None:
    """Initialize database with schema and seed reference data.
    
    Creates all tables, applies migrations, seeds meal catalog and canonical foods.
    """

def ensure_sqlite_column(cur: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    """Add column to table if it doesn't exist."""

def seed_reference_data(db_path: str) -> None:
    """Populate meal catalog and canonical food data."""

def _seed_meal_catalog(cur: sqlite3.Cursor, items: Sequence[MealCatalogItem]) -> None:
    """Insert meal catalog items (skips if already seeded)."""

def _seed_canonical_foods(cur: sqlite3.Cursor, records: Sequence[CanonicalFoodRecord]) -> None:
    """Insert canonical foods and alias/portion indices (skips if already seeded)."""
```

---

## 9. `platform/persistence/sqlite_repository.py` (Facade)

**Module**: Root repository facade composing domain-specific repositories

### Class

```python
class SQLiteRepository:
    def __init__(self, db_path: str = "dietary_guardian.db"):
        """Initialize database and compose repositories."""
```

**Attributes** (Composed Repositories):
- `medication: SQLiteMedicationRepository` - Medication storage
- `reminders: SQLiteReminderRepository` - Reminder storage
- `meals: SQLiteMealRepository` - Meal storage
- `clinical: SQLiteClinicalRepository` - Clinical/biomarker storage
- `catalog: SQLiteCatalogRepository` - Catalog/recommendation storage
- `alerts: SQLiteAlertRepository` - Alert storage
- `workflows: SQLiteWorkflowRepository` - Workflow storage

**Key Design**: 
- Single entry point (SQLiteRepository) for accessing all domain repositories
- Each domain repository is specialized and independently testable
- The facade pattern allows gradual migration from this structure to AppStores

---

## 10. `platform/persistence/sqlite_meal_repository.py`

**Module**: Meal records, observations, validated events, nutrition profiles

### Class

```python
class SQLiteMealRepository:
    def __init__(self, db_path: str) -> None
```

### Core Methods

**Record Management**:
- `save_meal_record(record: MealRecognitionRecord) -> None` - INSERT OR REPLACE
- `list_meal_records(user_id: str) -> list[MealRecognitionRecord]` - Merges legacy + v2 records
- `get_meal_record(user_id: str, meal_id: str) -> MealRecognitionRecord | None` - Checks legacy, then v2

**Observations**:
- `save_meal_observation(observation: RawObservationBundle) -> None`
- `list_meal_observations(user_id: str) -> list[RawObservationBundle]`

**Validated Events**:
- `save_validated_meal_event(event: ValidatedMealEvent) -> None`
- `list_validated_meal_events(user_id: str) -> list[ValidatedMealEvent]`
- `get_validated_meal_event(user_id: str, event_id: str) -> ValidatedMealEvent | None`

**Nutrition Profiles**:
- `save_nutrition_risk_profile(profile: NutritionRiskProfile) -> None`
- `list_nutrition_risk_profiles(user_id: str) -> list[NutritionRiskProfile]`
- `get_nutrition_risk_profile(user_id: str, event_id: str) -> NutritionRiskProfile | None`

### Internal Methods

- `_load_legacy_meal_records(user_id: str) -> list[MealRecognitionRecord]` - Load v1 format
- `_load_v2_meal_records(user_id: str) -> list[MealRecognitionRecord]` - Load v2 format, merge profiles
- `_build_meal_record_from_event(event: ValidatedMealEvent, profile: NutritionRiskProfile | None) -> MealRecognitionRecord` - Synthesize legacy format from new format

**Note**: Handles backward compatibility between meal record formats through synthesis.

---

## 11. `platform/persistence/sqlite_reminder_repository.py`

**Module**: Reminders, scheduled notifications, notification endpoints/logs, preferences, settings

### Class

```python
class SQLiteReminderRepository:
    def __init__(self, db_path: str) -> None
```

### Reminder Events

- `save_reminder_event(event: ReminderEvent) -> None`
- `get_reminder_event(event_id: str) -> ReminderEvent | None`
- `list_reminder_events(user_id: str) -> list[ReminderEvent]`

### Notification Preferences

- `list_reminder_notification_preferences(*, user_id: str, scope_type: str | None, scope_key: str | None) -> list[ReminderNotificationPreference]`
- `replace_reminder_notification_preferences(*, user_id: str, scope_type: str, scope_key: str | None, preferences: list[ReminderNotificationPreference]) -> list[ReminderNotificationPreference]`

### Scheduled Notifications

- `save_scheduled_notification(item: ScheduledReminderNotification) -> ScheduledReminderNotification` - INSERT OR IGNORE (idempotent)
- `get_scheduled_notification(notification_id: str) -> ScheduledReminderNotification | None`
- `list_scheduled_notifications(*, reminder_id: str | None, user_id: str | None) -> list[ScheduledReminderNotification]`
- `lease_due_scheduled_notifications(*, now: datetime, limit: int = 100) -> list[ScheduledReminderNotification]` - Atomically leases due notifications
- `set_scheduled_notification_trigger_at(notification_id: str, trigger_at: datetime) -> None`
- `mark_scheduled_notification_processing(notification_id: str, attempt_count: int) -> None`
- `mark_scheduled_notification_delivered(notification_id: str, attempt_count: int) -> None`
- `reschedule_scheduled_notification(notification_id: str, *, attempt_count: int, next_attempt_at: datetime, error: str) -> None`
- `mark_scheduled_notification_dead_letter(notification_id: str, *, attempt_count: int, error: str) -> None`
- `cancel_scheduled_notifications_for_reminder(reminder_id: str) -> int` - Returns count cancelled

### Notification Endpoints

- `replace_reminder_notification_endpoints(*, user_id: str, endpoints: list[ReminderNotificationEndpoint]) -> list[ReminderNotificationEndpoint]` - Deletes existing, inserts new
- `list_reminder_notification_endpoints(*, user_id: str) -> list[ReminderNotificationEndpoint]`
- `get_reminder_notification_endpoint(*, user_id: str, channel: str) -> ReminderNotificationEndpoint | None`

### Notification Logs

- `append_notification_log(entry: ReminderNotificationLogEntry) -> ReminderNotificationLogEntry`
- `list_notification_logs(*, reminder_id: str | None, scheduled_notification_id: str | None) -> list[ReminderNotificationLogEntry]`

### Mobility Settings

- `get_mobility_reminder_settings(user_id: str) -> MobilityReminderSettings | None`
- `save_mobility_reminder_settings(settings: MobilityReminderSettings) -> MobilityReminderSettings`

---

## 12. `platform/persistence/sqlite_medication_repository.py`

**Module**: Medication regimens and adherence events

### Class

```python
class SQLiteMedicationRepository:
    def __init__(self, db_path: str) -> None
```

### Regimens

- `save_medication_regimen(regimen: MedicationRegimen) -> None` - INSERT OR REPLACE
- `list_medication_regimens(user_id: str, *, active_only: bool = False) -> list[MedicationRegimen]`
- `get_medication_regimen(*, user_id: str, regimen_id: str) -> MedicationRegimen | None`
- `delete_medication_regimen(*, user_id: str, regimen_id: str) -> bool` - Returns success

### Adherence Events

- `save_medication_adherence_event(event: MedicationAdherenceEvent) -> MedicationAdherenceEvent`
- `list_medication_adherence_events(*, user_id: str, start_at: datetime | None, end_at: datetime | None) -> list[MedicationAdherenceEvent]`

**Note**: Regimens stored with JSON-serialized `slot_scope` field. Adherence events support date range filtering.

---

## 13. `platform/persistence/sqlite_clinical_repository.py`

**Module**: Biomarkers, symptoms, clinical cards, health profiles

### Class

```python
class SQLiteClinicalRepository:
    def __init__(self, db_path: str) -> None
```

### Biomarkers

- `save_biomarker_readings(user_id: str, readings: list[BiomarkerReading]) -> None` - Batch INSERT
- `list_biomarker_readings(user_id: str) -> list[BiomarkerReading]`

### Symptoms

- `save_symptom_checkin(checkin: SymptomCheckIn) -> SymptomCheckIn`
- `list_symptom_checkins(*, user_id: str, start_at: datetime | None, end_at: datetime | None, limit: int = 200) -> list[SymptomCheckIn]`

### Clinical Cards

- `save_clinical_card(card: ClinicalCardRecord) -> ClinicalCardRecord`
- `list_clinical_cards(*, user_id: str, limit: int = 50) -> list[ClinicalCardRecord]`
- `get_clinical_card(*, user_id: str, card_id: str) -> ClinicalCardRecord | None`

### Health Profiles

- `get_health_profile(user_id: str) -> HealthProfileRecord | None`
- `save_health_profile(profile: HealthProfileRecord) -> HealthProfileRecord`
- `get_health_profile_onboarding_state(user_id: str) -> HealthProfileOnboardingState | None`
- `save_health_profile_onboarding_state(state: HealthProfileOnboardingState) -> HealthProfileOnboardingState`

---

## 14. `platform/persistence/sqlite_catalog_repository.py`

**Module**: Meal catalog, canonical foods, recommendations, suggestions, preferences

### Class

```python
class SQLiteCatalogRepository:
    def __init__(self, db_path: str) -> None
```

### Meal Catalog

- `list_meal_catalog_items(*, locale: str, slot: str | None, limit: int = 100) -> list[MealCatalogItem]` - Active only
- `get_meal_catalog_item(meal_id: str) -> MealCatalogItem | None`

### Canonical Foods

- `list_canonical_foods(*, locale: str, slot: str | None, limit: int = 100) -> list[CanonicalFoodRecord]` - Active only
- `get_canonical_food(food_id: str) -> CanonicalFoodRecord | None`
- `find_food_by_name(*, locale: str, name: str) -> CanonicalFoodRecord | None` - Normalizes name, checks aliases, falls back to full search

### Recommendations

- `save_recommendation(user_id: str, payload: dict[str, Any]) -> None`

### Recommendation Interactions

- `save_recommendation_interaction(interaction: RecommendationInteraction) -> RecommendationInteraction`
- `list_recommendation_interactions(user_id: str, *, limit: int = 200) -> list[RecommendationInteraction]`

### Preferences

- `get_preference_snapshot(user_id: str) -> PreferenceSnapshot | None`
- `save_preference_snapshot(snapshot: PreferenceSnapshot) -> PreferenceSnapshot`

### Suggestions

- `save_suggestion_record(user_id: str, payload: dict[str, Any]) -> dict[str, Any]` - Validates suggestion_id and created_at
- `list_suggestion_records(user_id: str, limit: int = 20) -> list[dict[str, Any]]`
- `get_suggestion_record(user_id: str, suggestion_id: str) -> dict[str, Any] | None`

---

## 15. `platform/persistence/sqlite_alert_repository.py`

**Module**: Alert outbox persistence with lease-based delivery

### Class

```python
class SQLiteAlertRepository:
    def __init__(self, db_path: str) -> None
```

### Outbox Operations

- `enqueue_alert(message: AlertMessage) -> list[OutboxRecord]` - Creates outbox entry per destination with idempotency key
- `lease_alert_records(now: datetime, lease_owner: str, lease_seconds: int, limit: int, alert_id: str | None = None) -> list[OutboxRecord]` - Atomically leases pending/processing records and sets state=processing
- `mark_alert_delivered(alert_id: str, sink: str, attempt_count: int | None = None) -> None` - Sets state=delivered
- `reschedule_alert(alert_id: str, sink: str, next_attempt_at: datetime, attempt_count: int, error: str) -> None` - Sets state=pending with retry time
- `mark_alert_dead_letter(alert_id: str, sink: str, error: str, attempt_count: int | None = None) -> None` - Sets state=dead_letter

### Query

- `list_alert_records(alert_id: str | None = None) -> list[OutboxRecord]` - Lists all records, optionally filtered by alert_id

**Design Pattern**: Transactional outbox with lease-based concurrency control for reliable alert delivery.

---

## 16. `platform/persistence/sqlite_workflow_repository.py`

**Module**: Workflow tool policies, contract snapshots, timeline events

### Class

```python
class SQLiteWorkflowRepository:
    def __init__(self, db_path: str) -> None
```

### Tool Role Policies

- `save_tool_role_policy(record: ToolRolePolicyRecord) -> ToolRolePolicyRecord` - INSERT with ON CONFLICT UPDATE
- `list_tool_role_policies(*, role: str | None, agent_id: str | None, tool_name: str | None, enabled_only: bool = False) -> list[ToolRolePolicyRecord]` - Ordered by priority DESC, updated_at DESC
- `get_tool_role_policy(policy_id: str) -> ToolRolePolicyRecord | None`

### Workflow Contract Snapshots

- `save_workflow_contract_snapshot(snapshot: WorkflowContractSnapshotRecord) -> WorkflowContractSnapshotRecord` - Serializes workflows/agents as JSON
- `list_workflow_contract_snapshots(*, limit: int = 50) -> list[WorkflowContractSnapshotRecord]` - Ordered by version DESC
- `get_workflow_contract_snapshot(*, version: int) -> WorkflowContractSnapshotRecord | None`

### Workflow Timeline Events

- `save_workflow_timeline_event(event: WorkflowTimelineEvent) -> WorkflowTimelineEvent`
- `list_workflow_timeline_events(*, correlation_id: str | None, user_id: str | None) -> list[WorkflowTimelineEvent]` - Ordered by created_at

---

## 17. `platform/persistence/evidence/static_retriever.py`

**Module**: Static evidence retrieval for LLM context generation

### Class

```python
class StaticEvidenceRetriever:
    def search_evidence(
        self,
        *,
        interaction_type: InteractionType,
        message: str,
        snapshot: CaseSnapshot,
        personalization: PersonalizationContext,
    ) -> EvidenceBundle:
        """Retrieve evidence citations based on interaction context."""
```

### Logic

- Parses `interaction_type` and searches for keywords in message and risk flags
- Conditionally adds citations for:
  - **Hawker meal risk**: Low-sodium, less-oily swaps (confidence: 0.81)
  - **Medication adherence**: Friction-reducing reminders (confidence: 0.84)
  - **Biomarker follow-up**: Abnormal patterns rationale (confidence: 0.86)
  - **Default**: Longitudinal coaching guidance (confidence: 0.72)

**Returns**: `EvidenceBundle` with query string, personalized guidance summary, and ranked citations

---

## 18. `platform/persistence/food/hybrid_search.py`

**Module**: Hybrid food search with vector embeddings and keyword reranking

### Class

```python
class FoodHybridSearch:
    def __init__(
        self,
        vector_top_k: int = 20,
        candidate_multiplier: int = 4,
        vectorstore_dir: str | None = None,
        model_name: str | None = None,
    ) -> None:
        """Initialize vector search with ChromaDB and sentence transformers."""
```

**Configuration**:
- `EMBEDDING_MODEL` = "BAAI/bge-m3"
- `FOOD_COLLECTION` = "sg_food_local"
- `DISEASE_KEYWORDS` - Maps diseases to search terms

### Methods

- `search(query: str, top_k: int = 5) -> list[dict[str, Any]]` - Main entry point
- `_vector_search(*, query: str, disease: str | None, top_k: int) -> list[dict[str, Any]]` - ChromaDB similarity search
- `_keyword_rerank(*, query: str, candidates: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]` - Reranks by keyword overlap
- `_tokenize(text: str) -> list[str]` - Tokenizes English and Chinese text
- `_infer_disease(query: str) -> str | None` - Extracts disease hint from query

### Scoring

Combines:
- **Keyword Score** (40%): Coverage + phrase match + name boost
- **Vector Score** (60%): Cosine similarity from embeddings

**Graceful Degradation**: Falls back to keyword-only if vectors unavailable

---

## 19. `platform/persistence/food/ingestion.py`

**Module**: Food data loading and transformation utilities

### Helper Functions

- `_normalize_text(value: str) -> str` - Lowercases, removes non-alphanumeric, normalizes whitespace
- `_nutrition_from_source(payload: dict[str, Any]) -> Nutrition` - Extracts and converts nutrition fields
- `_risk_tags(nutrition: Nutrition) -> list[str]` - Tags high sodium (≥900mg), sugar (≥15g), protein (≥20g), fiber (≥5g)
- `_read_json_array(path: Path) -> list[dict[str, Any]]` - Safely reads JSON array file
- `_portion(unit: str, grams: float) -> list[PortionReference]` - Creates portion reference
- `_slot(value: str) -> MealSlot` - Normalizes meal slot value
- `_scale_nutrition(nutrition: Nutrition, factor: float) -> Nutrition` - Scales nutrition by factor

### Data Loaders

- `load_usda_records(path: Path) -> list[CanonicalFoodRecord]` - Ingests USDA FoodData Central format
- `load_open_food_facts_records(path: Path) -> list[CanonicalFoodRecord]` - Ingests Open Food Facts format with per-100g conversion

---

## 20. `platform/persistence/food/local_ingest.py`

**Module**: Singapore hawker food vectorization and ingestion

### Classes

#### `HawkerChunker`
**Purpose**: Chunks hawker food records into embeddings-ready documents

**Static Method**:
```python
chunk(food: dict) -> list[dict]:
    """Produces nutrition, disease advice, and alternatives chunks."""
```

Creates chunks for:
- **Nutrition**: Food names (EN/CN/Malay), category, serving, detailed macros/micros, health tags
- **Disease Advice**: Per-disease guidance (diabetes, hypertension, etc.) with risk level
- **Alternatives**: Healthier substitution suggestions

#### `DrinkChunker`
**Purpose**: Chunks kopitiam drink guide into embeddings-ready documents

**Static Method**:
```python
chunk(data: dict) -> list[dict]:
    """Produces drink info, disease recommendations, and ordering tips chunks."""
```

Creates chunks for:
- **Drink Info**: Terminology, calories, sugar content, notes
- **Disease Recommendations**: Best/acceptable/limit/avoid categories
- **Ordering Tips**: Useful phrases in English, Chinese, Malay

#### `FoodInfoIngester`
**Purpose**: Ingests hawker/drink data into ChromaDB

**Methods**:
- `__init__()` - Initializes ChromaDB client and collection
- `_upsert_chunks(chunks: list[dict]) -> None` - Batch upserts with embeddings
- `ingest_hawker() -> None` - Loads sg_hawker_food.json and chunks
- `ingest_drinks() -> None` - Loads sg_drinks_and_tips.json and chunks
- `run() -> None` - Orchestrates full ingestion

**Data Files**:
- `HAWKER_JSON` = `data/food/sg_hawker_food.json`
- `DRINKS_JSON` = `data/food/sg_drinks_and_tips.json`

---

## 21. `platform/persistence/food/local_retriever.py`

**Module**: Singapore food/drink vector database query interface

### Constants

```python
VECTORSTORE_DIR = BASE_DIR / "data" / "vectorstore" / "chroma_db"
COLLECTION_NAME = "sg_food_local"
EMBEDDING_MODEL = "BAAI/bge-m3"
```

### Class

```python
class FoodInfoRetriever:
    def __init__(self, n_results: int = 4) -> None:
        """Initialize ChromaDB client and collection."""
```

**Methods**:
- `_get_model() -> SentenceTransformer` - Lazy loads embedding model
- `retrieve(query: str) -> list[dict[str, Any]]` - Returns top-k matching chunks with distance
- `format_for_context(query: str) -> str | None` - Formats results as markdown for LLM context

**Output Format**:
```
## Local Singapore Food Database (exact nutritional data)

**[Local-1] {Food Name}** (relevance: {percentage}%)
{Chunk text}
```

---

## 22. `platform/persistence/household/sqlite_store.py`

**Module**: Household management persistence

### Class

```python
class SQLiteHouseholdStore:
    def __init__(self, db_path: str) -> None:
        """Initialize household database with schema and indices."""
```

**Tables**:
- `households` - Household records with owner
- `household_members` - User membership with role and join date
- `household_invites` - Invite codes with expiration and usage limits

### Household Operations

- `get_household_for_user(user_id: str) -> dict[str, Any] | None` - Gets user's household
- `get_household_by_id(household_id: str) -> dict[str, Any] | None` - Gets household by ID
- `create_household(*, owner_user_id: str, owner_display_name: str, name: str) -> dict[str, Any]` - Creates household with owner
- `rename_household(*, household_id: str, name: str) -> dict[str, Any] | None` - Renames household

### Member Operations

- `list_members(household_id: str) -> list[dict[str, Any]]` - Lists members ordered by role, join date
- `get_member_role(household_id: str, user_id: str) -> str | None` - Gets user's role
- `remove_member(*, household_id: str, user_id: str) -> bool` - Removes member

### Invite Operations

- `create_invite(*, household_id: str, created_by_user_id: str) -> dict[str, Any]` - Creates 7-day invite code (max 10 uses)
- `join_by_invite(*, code: str, user_id: str, display_name: str) -> tuple[dict[str, Any], bool] | None` - Joins via code, returns (household, is_new_join)

**Idempotency**: join_by_invite returns existing household if user already member

---

## 23. `platform/scheduling/coordination/in_memory.py`

**Module**: In-process coordination store for locks and signals

### Class

```python
class InMemoryCoordinationStore:
    def __init__(self) -> None:
        """Initialize lock and signal tracking with thread safety."""
```

**Attributes** (Private):
- `_signals: dict[str, list[dict[str, Any]]]` - Channel → signal queue
- `_locks: dict[str, tuple[str, datetime]]` - Key → (owner, expires_at)
- `_lock: Lock` - Thread synchronization
- `_condition: Condition` - Wait/notify for signals

### Methods

**Locks**:
- `acquire_lock(key: str, *, owner: str, ttl_seconds: int) -> bool` - CAS-style acquisition with TTL
- `release_lock(key: str, *, owner: str) -> bool` - Owner-verified release

**Signals**:
- `publish_signal(channel: str, payload: dict[str, Any]) -> None` - Enqueues signal, notifies waiters
- `drain_signals(channel: str) -> list[dict[str, Any]]` - Dequeues all signals
- `wait_for_signal(channel: str, *, timeout_seconds: float) -> dict[str, Any] | None` - Blocks for one signal

**Lifecycle**:
- `close() -> None` - No-op (compatibility method)

**Use Case**: Testing and single-process deployments

---

## 24. `platform/scheduling/coordination/redis_coordination.py`

**Module**: Distributed coordination via Redis

### Class

```python
class RedisCoordinationStore:
    def __init__(self, *, redis_url: str, namespace: str) -> None:
        """Initialize Redis client with namespace routing."""
```

**Key Routing**: Domains requests by key name:
- "reminder" → reminder domain
- "outbox", "workflow", "worker" → workflow domain
- "notification" → notification domain
- default → coordination domain

### Methods

**Locks**:
- `acquire_lock(key: str, *, owner: str, ttl_seconds: int) -> bool` - Redis SET NX with EX
- `release_lock(key: str, *, owner: str) -> bool` - Lua script for owner verification

**Signals** (Queue-based):
- `publish_signal(channel: str, payload: dict[str, Any]) -> None` - LPUSH (prepend)
- `drain_signals(channel: str) -> list[dict[str, Any]]` - RPOP all (fifo)
- `wait_for_signal(channel: str, *, timeout_seconds: float) -> dict[str, Any] | None` - BRPOP (blocking)

**Lifecycle**:
- `close() -> None` - Closes Redis connection

**Lua Script** (release_lock):
```lua
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
```

**Use Case**: Multi-process/distributed deployments with shared state

---

## 25. `platform/scheduling/schedulers/reminder_scheduler.py`

**Module**: Reminder scheduling runtime loop

### Result Class

```python
@dataclass(slots=True)
class ReminderSchedulerRunResult:
    queued_count: int          # Reminders queued
    delivery_attempts: int     # Notifications sent
```

### Functions

```python
async def run_reminder_scheduler_once(
    *,
    repository: ReminderSchedulerRepository | AppStoreBackend | None = None,
    now: datetime | None = None,
) -> ReminderSchedulerRunResult:
    """Dispatch due reminders and process outbox once.
    
    Performs one scheduling iteration:
    1. Dispatches due reminder notifications (up to batch size)
    2. Processes alert outbox for those notifications
    
    Returns: Result with counts of queued and delivered notifications
    """

async def run_reminder_scheduler_loop() -> None:
    """Run reminder scheduler in infinite loop.
    
    Calls run_reminder_scheduler_once repeatedly at configured interval.
    Logs startup parameters.
    """
```

**Configuration** (from AppSettings):
- `workers.reminder_scheduler_interval_seconds` - Loop sleep time
- `workers.reminder_scheduler_batch_size` - Max reminders per iteration
- `workers.alert_worker_max_attempts` - Retry limit for alerts
- `workers.alert_worker_concurrency` - Parallel delivery tasks

**Exports**:
- `ReminderSchedulerRunResult`
- `run_reminder_scheduler_loop`
- `run_reminder_scheduler_once`

**Use Case**: Background process for dispatching and delivering reminder notifications

---

## Module Dependency Graph

```
__init__.py
  ├─ builders.py ─→ sqlite_app_store.py ─→ sqlite_repository.py
  ├─ contracts.py
  ├─ domain_stores.py ─→ protocols.py
  ├─ runtime_bootstrap.py ─→ builders.py
  └─ protocols.py

sqlite_repository.py (Facade)
  ├─ sqlite_meal_repository.py
  ├─ sqlite_reminder_repository.py
  ├─ sqlite_medication_repository.py
  ├─ sqlite_clinical_repository.py
  ├─ sqlite_catalog_repository.py
  ├─ sqlite_alert_repository.py
  └─ sqlite_workflow_repository.py

sqlite_bootstrap.py (Schema & Seeds)
  └─ ingestion.py, local_ingest.py

Food Submodule
  ├─ hybrid_search.py (Vector search)
  ├─ local_ingest.py (Data ingestion)
  ├─ local_retriever.py (Query interface)
  └─ ingestion.py (Utilities)

Household Submodule
  └─ sqlite_store.py

Scheduling Submodule
  ├─ coordination/
  │   ├─ in_memory.py (Testing)
  │   └─ redis_coordination.py (Production)
  └─ schedulers/
      └─ reminder_scheduler.py (Runtime loop)
```

---

## Key Design Patterns

1. **Facade Pattern**: `AppStores` aggregates domain stores; `SQLiteRepository` composes domain repositories

2. **Protocol-Based Interfaces**: Structural typing with `Protocol` enables loose coupling

3. **Factory Functions**: `build_*` functions support dependency injection

4. **Transactional Outbox**: Alert repository uses lease-based concurrency for reliable delivery

5. **Backward Compatibility**: Meal repository synthesizes legacy format from v2 data

6. **Hybrid Search**: Combines vector embeddings with keyword reranking for food discovery

7. **Graceful Degradation**: Food search falls back to keyword-only if vectors unavailable

8. **Thread-Safe Coordination**: In-memory store uses locks/conditions; Redis for distributed systems

9. **Idempotency**: Scheduled notifications use idempotency keys; household joins check existing membership

10. **Domain Routing**: Redis coordination stores route by domain for better isolation

---

## Testing Considerations

- In-memory coordination store enables single-process testing
- Protocol-based interfaces allow mock implementations
- Meal repository backward compatibility layer ensures data migration safety
- Household store uses UUID generation for ID uniqueness
- Alert repository lease mechanism prevents duplicate delivery in concurrent scenarios