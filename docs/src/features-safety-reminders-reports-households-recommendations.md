# Dietary Guardian Module Reference Documentation

## Overview

This is comprehensive documentation for the **dietary_guardian** module, a health-focused meal analysis and recommendation system with safety validation, reminders, reports, household management, and personalized recommendations.

---

## 1. Safety Features Module (`features/safety/`)

### 1.1 Domain Layer

#### `engine.py` - SafetyEngine
**Class: `SafetyEngine`**
- **Constructor**: `__init__(user: UserProfile, db: DrugInteractionRepository | None = None)`
- **Methods**:
  - `validate_meal(meal: MealEvent | MealState) -> list[str]`: Validates meal against user's medical conditions and medications
    - Checks sodium/sugar thresholds
    - Detects hypoglycemia risk for glucose-lowering medications (insulin, glibenclamide, gliclazide)
    - Performs database-backed clinical contraindication checks
    - Returns list of warning strings
    - Raises `SafetyViolation` for critical violations
  - `_contains_item(ingredients: list[str], item: str) -> bool`: Helper for ingredient matching

#### `exceptions.py` - Exception Classes
- **`SafetyViolation(message: str, level: str = "Critical", reason: str = "")`**
  - Raised for critical safety violations
  - Attributes: `message`, `level`, `reason`

- **`HumanInTheLoopException(message: str, meal_state: MealState | None = None)`**
  - Raised when automated perception confidence is too low
  - Attributes: `message`, `meal_state` (optional partial MealState)

#### `ports.py` - Protocols
- **`DrugInteractionRepository`** (Protocol)
  - `get_contraindications(medication_name: str) -> list[tuple[str, str, str]]`: Returns (restricted_item, reason, severity)

- **`SafetyPort`** (Protocol)
  - `validate_meal(meal: MealEvent) -> list[str]`: Return warnings or raise SafetyViolation

#### `thresholds.py` - Safety Constants
- `SODIUM_WARNING_FRACTION = 0.5` (50% of daily limit)
- `SUGAR_WARNING_FRACTION = 0.3` (30% of daily limit)
- `HYPOGLYCEMIA_LOW_CARB_THRESHOLD_G = 10.0` (grams)

#### `triage.py` - Text Safety Evaluation
- **`SafetyDecision`** (dataclass)
  - `decision: str` (e.g., "escalate", "allow")
  - `reasons: list[str]` (matched red flag rules)
  - `required_actions: list[str]`
  - `redactions: list[str]` (fields to redact)

- **`evaluate_text_safety(text: str) -> SafetyDecision`**
  - Detects red flags: chest pain, trouble breathing, stroke signs, suicidal ideation, allergic reactions, loss of consciousness, severe bleeding
  - Returns escalation decision with required actions

#### `alerts/models.py` - Alert Models
- **`AlertSeverity`**: Literal["info", "warning", "critical"]
- **`OutboxState`**: Literal["pending", "processing", "delivered", "dead_letter"]

- **`AlertMessage`** (Pydantic BaseModel)
  - `alert_id: str`, `type: str`, `severity: AlertSeverity`
  - `payload: dict[str, str]`, `destinations: list[str]`
  - `correlation_id: str`, `created_at: datetime`

- **`OutboxRecord`** (Pydantic BaseModel)
  - Extends AlertMessage with: `state: OutboxState`, `attempt_count: int`
  - `next_attempt_at: datetime`, `last_error: str | None`
  - `lease_owner: str | None`, `lease_until: datetime | None`, `idempotency_key: str`

- **`AlertDeliveryResult`** (Pydantic BaseModel)
  - `alert_id: str`, `sink: str`, `success: bool`, `attempt: int`
  - `destination: str | None`, `provider_reference: str | None`, `error: str | None`

### 1.2 Infrastructure Layer

#### `infra/drug_interaction_db.py` - DrugInteractionDB
**Class: `DrugInteractionDB`**
- **Constructor**: `__init__(db_path: str = "clinical_safety.db")`
- **Methods**:
  - `get_contraindications(medication_name: str) -> list[tuple[str, str, str]]`: Returns contraindications with caching
  - `_init_db()`: Creates schema and seeds clinical data
  - `_seed_data(cursor)`: Seeds initial data for:
    - Medications: Warfarin, Metformin, Atorvastatin, Amlodipine, Insulin, Phenelzine
    - Contraindications: Food-drug interactions with severity levels

**Database Schema**:
- `safety_metadata`: key-value store
- `medications`: id, name, common_brands
- `contraindications`: med_id, restricted_item, reason, severity

### 1.3 Service Layer

#### `service.py` - Safety Service
- **Exports**: 
  - `apply_safety_decision`
  - `review_care_plan`

#### `use_cases.py` - Use Cases

**`review_care_plan(*, interaction: CompanionInteraction, snapshot: CaseSnapshot, engagement: EngagementAssessment, care_plan: CarePlan) -> SafetyDecision`**
- Evaluates policy status: "approved", "escalate", or "adjusted"
- Checks for symptom escalation, biomarker risks, adherence issues
- Returns SafetyDecision with reasons and actions

**`apply_safety_decision(*, care_plan: CarePlan, decision: SafetyDecision) -> CarePlan`**
- Applies safety decision to modify care plan
- Escalates or adjusts actions based on decision status
- Returns updated CarePlan

---

## 2. Reminders Features Module (`features/reminders/`)

### 2.1 Domain Layer - Models

#### `domain/models.py` - Reminder Models
- **`MobilityReminderSettings`** (Pydantic BaseModel)
  - `user_id: str`, `enabled: bool`, `interval_minutes: int`
  - `active_start_time: str` (HH:MM format)
  - `active_end_time: str` (HH:MM format)

- **Type Aliases**:
  - `ReminderNotificationChannel`: "in_app", "email", "sms", "push", "telegram", "whatsapp", "wechat"
  - `NotificationPreferenceScope`: "default" or "reminder_type"
  - `ScheduledNotificationStatus`: "pending", "queued", "processing", "retry_scheduled", "delivered", "dead_letter", "cancelled"
  - `NotificationLogEventType`: "scheduled", "queued", "dispatch_started", "delivered", "retry_scheduled", "dead_lettered", "cancelled"

- **`ReminderNotificationEndpoint`** (Pydantic BaseModel)
  - `id: str`, `user_id: str`, `channel: ReminderNotificationChannel`
  - `destination: str`, `verified: bool`, `created_at: datetime`, `updated_at: datetime`

- **`ReminderNotificationPreference`** (Pydantic BaseModel)
  - `id: str`, `user_id: str`, `scope_type: NotificationPreferenceScope`
  - `scope_key: str | None`, `channel: ReminderNotificationChannel`
  - `offset_minutes: int`, `enabled: bool`, `created_at: datetime`, `updated_at: datetime`

- **`ScheduledReminderNotification`** (Pydantic BaseModel)
  - `id: str`, `reminder_id: str`, `user_id: str`, `channel: ReminderNotificationChannel`
  - `trigger_at: datetime`, `offset_minutes: int`, `status: ScheduledNotificationStatus`
  - `attempt_count: int`, `payload: dict[str, object]`, `idempotency_key: str`
  - `last_error: str | None`, `delivered_at: datetime | None`

- **`ReminderEvent`** (Pydantic BaseModel)
  - `id: str`, `user_id: str`, `reminder_type: ReminderType` ("medication" or "mobility")
  - `title: str`, `body: str | None`, `medication_name: str`, `dosage_text: str`
  - `scheduled_at: datetime`, `slot: MealSlot | None`, `status: ReminderStatus` ("sent", "acknowledged", "missed")
  - `meal_confirmation: MealConfirmation` ("yes", "no", "unknown")
  - `sent_at: datetime | None`, `ack_at: datetime | None`

- **`MedicationRegimen`** (Pydantic BaseModel)
  - `id: str`, `user_id: str`, `medication_name: str`, `dosage_text: str`
  - `timing_type: TimingType` ("pre_meal", "post_meal", "fixed_time")
  - `offset_minutes: int`, `slot_scope: list[MealSlot]`, `fixed_time: str | None`
  - `max_daily_doses: int`, `active: bool`

### 2.2 Notifications Layer

#### `notifications/alert_dispatch.py` - Alert Dispatch
**Functions**:

- **`send_in_app(reminder_event: ReminderEvent) -> DeliveryResult`**
  - Sends reminder to in-app inbox

- **`send_push(reminder_event: ReminderEvent, force_fail: bool = False) -> DeliveryResult`**
  - Sends push notification (simulated in current implementation)

- **`dispatch_reminder(reminder_event, channels, retries=2, force_push_fail=False, repository=None) -> list[DeliveryResult]`**
  - Primary entry point for reminder delivery (v1 direct or v2 outbox-backed)
  - Supports multiple channels with retry logic

- **`dispatch_reminder_async(reminder_event, channels, repository=None, retries=None, force_push_fail=False) -> list[DeliveryResult]`**
  - Enqueues reminder into alert outbox and drains synchronously

- **`trigger_alert(*, alert_type, severity, payload, destinations, repository) -> tuple[AlertMessage, list[DeliveryResult]]`**
  - General-purpose alert triggering with outbox integration

**Models**:
- **`DeliveryResult`** (Pydantic BaseModel)
  - `event_id: str`, `channel: str`, `success: bool`, `attempts: int`
  - `error: str | None`, `delivered_at: datetime | None`, `destination: str | None`

#### `notifications/alert_session.py` - Session Alert Orchestration
- **`trigger_alert_for_session(*, deps, session, payload, request_id, correlation_id) -> AlertTriggerResponse`**
- **`get_alert_timeline(*, deps, alert_id) -> AlertTimelineResponse`**

#### `notifications/reminder_materialization.py` - Materialization & Dispatch
- **`resolve_notification_preferences(*, repository, user_id, reminder_type) -> list[ReminderNotificationPreference]`**
  - Resolves effective preferences with fallback to defaults or system default (in_app)

- **`materialize_reminder_notifications(*, repository, reminder_event, reminder_type) -> list[ScheduledReminderNotification]`**
  - Converts ReminderEvent into ScheduledReminderNotification rows per preference

- **`dispatch_due_reminder_notifications(*, repository, now=None, limit=100) -> list[QueuedReminderNotification]`**
  - Leases due notifications and enqueues into alert outbox

- **`cancel_reminder_notifications(*, repository, reminder_id) -> int`**
  - Cancels all pending notifications for a reminder

**CRUD Functions**:
- `list_notification_preferences(...) -> ReminderNotificationPreferenceListResponse`
- `replace_notification_preferences(...) -> ReminderNotificationPreferenceListResponse`
- `list_reminder_notification_schedules(...) -> ScheduledReminderNotificationListResponse`
- `list_notification_endpoints(...) -> ReminderNotificationEndpointListResponse`
- `replace_notification_endpoints(...) -> ReminderNotificationEndpointListResponse`
- `list_reminder_notification_logs(...) -> ReminderNotificationLogListResponse`

#### `notifications/reminders.py` - Reminder Use Cases
- **`generate_reminders_for_session(*, context, session) -> ReminderGenerateResponse`**
  - Generates daily medication + mobility reminders for session user
  - Materializes notification schedules
  - Publishes coordination signals

- **`list_reminders_for_session(*, context, user_id) -> ReminderListResponse`**
  - Lists all reminder events for user with metrics

- **`confirm_reminder_for_session(*, context, user_id, event_id, confirmed) -> ReminderConfirmResponse`**
  - Marks medication reminder as confirmed/unconfirmed
  - Cancels notifications and updates metrics

- **`get_mobility_settings_for_session(*, context, user_id) -> MobilityReminderSettingsEnvelopeResponse`**

- **`update_mobility_settings_for_session(*, context, user_id, payload) -> MobilityReminderSettingsEnvelopeResponse`**

#### `notifications/use_cases.py` - Notification Feeds
- **`NotificationReadStateStore`** (dataclass with thread-safe read state management)
  - `is_read(*, user_id, notification_id) -> bool`
  - `mark_read(*, user_id, notification_id) -> None`
  - `mark_all(*, user_id, notification_ids) -> int` (returns count of newly marked)

- **`list_notifications(*, context, user_id) -> NotificationListResponse`**
  - Lists workflow timeline events as notifications
  - Returns with unread counts

- **`mark_notification_read(*, context, user_id, notification_id) -> NotificationMarkReadResponse | None`**

- **`mark_all_notifications_read(*, context, user_id) -> NotificationMarkAllReadResponse`**

### 2.3 Outbox Layer

#### `outbox/enums.py` - Enumerations
| Enum | Values |
|------|--------|
| `ReminderState` | SCHEDULED, ENQUEUED, SENT, DELIVERED, ACKED, SNOOZED, IGNORED, FAILED, ESCALATED |
| `ReminderType` | MEDICATION, THRESHOLD_ALERT, MEASUREMENT, FOOD_RECORD |
| `MetricType` | HEART_RATE, BLOOD_GLUCOSE |
| `ReminderChannel` | TELEGRAM, WHATSAPP, SMS, EMAIL, IN_APP |
| `MealType` | BREAKFAST, LUNCH, DINNER, SNACK |

#### `outbox/models.py` - Outbox Domain Models
- **`ThresholdRule`** (frozen dataclass)
  - `metric_type: MetricType`, `min_value: float | None`, `max_value: float | None`
  - `unit: str`, `alert_title: str`
  - `evaluate(value: float) -> str | None`: Returns alert reason or None

- **`ReminderEvent`** (frozen dataclass)
  - `event_id: str`, `user_id: str`, `reminder_id: str`, `reminder_type: ReminderType`
  - `scheduled_at: str`, `channel: str`, `payload: str` (JSON), `idempotency_key: str`
  - `correlation_id: str`, `created_at: str`
  - `@classmethod create(...)`: Factory with UUID generation

- **`Reminder`** (dataclass)
  - `reminder_id: str`, `user_id: str`, `reminder_type: ReminderType`, `state: ReminderState`
  - `message: str`, `scheduled_at: str`, `created_at: str`, `payload: dict[str, Any]`
  - `to_record() -> dict`: Serialization helper
  - `mark(state: ReminderState) -> None`

- **`MetricReading`** (frozen dataclass)
  - `user_id: str`, `metric_type: MetricType`, `metric_value: float`, `unit: str`
  - `measured_at: str`, `source: str`, `raw_payload: dict[str, Any]`

- **`FoodRecord`** (frozen dataclass)
  - `user_id: str`, `meal_type: str`, `foods: list[str]`, `recorded_at: str`, `note: str`

- **`ReminderDispatchResult`** (frozen dataclass)
  - `success: bool`, `provider_msg_id: str | None`, `error: str | None`

#### `outbox/service.py` - ReminderService
**Class: `ReminderService`**
- **Fields**:
  - `reminder_repo: ReminderRepository`, `outbox_repo: OutboxRepository`
  - `metric_repo: MetricReadingRepository`, `food_repo: FoodRecordRepository`
  - `delivery: DeliveryPort`, `drug_knowledge: DrugKnowledgePort`
  - `default_channel: str = ReminderChannel.TELEGRAM.value`

- **Methods**:
  - `schedule_medication_task(...) -> Reminder | None`: Drug-aware medication scheduling
  - `check_threshold_and_wake(...) -> Reminder | None`: Metric threshold evaluation & alert
  - `schedule_measurement_reminder(...) -> Reminder`: Measurement task generation
  - `ensure_measurement_reminder_if_missing(...) -> Reminder | None`: Conditional scheduling
  - `record_food_intake(...)`: Logs food consumption
  - `schedule_food_record_reminder(...) -> Reminder`
  - `ensure_food_record_reminder_if_missing(...) -> Reminder | None`: Conditional scheduling
  - `intercept_food_risk(...) -> dict[str, str] | None`: Drug-food interaction detection
  - `confirm_task(...) -> bool`: Medication confirmation
  - `dispatch_due_events(...) -> list[ReminderDispatchResult]`: Batch event delivery

#### `outbox/infra/delivery.py` - Delivery Adapters
- **`TelegramDeliveryConfig`** (frozen dataclass)
  - `bot_token: str`, `chat_id: str`, `dev_mode: bool = True`

- **`MockDeliveryAdapter`**: Safe development/testing adapter

- **`TelegramDeliveryAdapter`**: Telegram-specific (dev mode or live API placeholder)

- **`WebhookDeliveryAdapter`**: Generic webhook fallback

- **`build_delivery_adapter(channel, telegram_bot_token, ...) -> Any`**: Factory function

#### `outbox/infra/knowledge.py` - Drug Knowledge Repository
- **`JsonDrugKnowledgeRepository`**
  - Loads drug reference data from JSON files
  - `get_drug_info(query: str) -> dict[str, Any] | None`: Fuzzy matching
  - `list_all_drugs() -> list[dict[str, Any]]`

- **`EmptyDrugKnowledgeRepository`**: Null object fallback

#### `outbox/infra/outbox_sqlite.py` - SQLite Outbox Persistence
- **`SQLiteOutboxRepository`**
  - `enqueue(event: ReminderEvent) -> None`
  - `fetch_due_events(now: str, limit: int) -> list[ReminderEvent]`
  - `mark_sent(event_id: str, provider_msg_id: str | None) -> None`
  - `mark_failed(event_id: str, reason: str) -> None`
  - `retry_failed(*, event_id: str | None) -> int`: Resets failed events to PENDING
  - `get_event_status(event_id: str) -> dict[str, str | None] | None`

#### `outbox/infra/repository.py` - Unified SQLite Reminder Repository
- **`SQLiteReminderRepository`**: Implements all three protocols
  - **ReminderRepository methods**:
    - `save_reminder(reminder: Reminder) -> None`
    - `update_state(reminder_id: str, state: ReminderState) -> None`
    - `get_reminder(reminder_id: str) -> dict[str, Any] | None`
    - `list_reminders(...) -> list[dict[str, Any]]`
    - `log_confirmation(reminder_id: str, is_taken: bool, timestamp: str) -> None`
    - `get_latest_confirmation(reminder_id: str) -> dict[str, Any] | None`

  - **MetricReadingRepository methods**:
    - `log_metric_reading(reading: MetricReading) -> None`
    - `get_last_metric_reading(user_id: str, metric_type: str) -> dict[str, Any] | None`
    - `list_metric_readings(...) -> list[dict[str, Any]]`

  - **FoodRecordRepository methods**:
    - `log_food_record(record: FoodRecord) -> None`
    - `get_latest_food_record(user_id: str, meal_type: str | None) -> dict[str, Any] | None`
    - `list_food_records(...) -> list[dict[str, Any]]`

### 2.4 Service Layer

#### `service.py` - Reminders Service
**Exports**: All functions from `notifications/reminders.py`

---

## 3. Reports Features Module (`features/reports/`)

### 3.1 Domain Layer

#### `domain/biomarker_parsing.py` - Report Parsing
**Constants**:
- `SUPPORTED_BIOMARKER_PATTERNS`: Regex patterns for hba1c, fasting_glucose, ldl, hdl, triglycerides, systolic_bp, diastolic_bp, creatinine

**Functions**:

- **`parse_report_input(report_input: ReportInput) -> list[BiomarkerReading]`**
  - Extracts biomarker readings from pasted text or PDF
  - Returns list of BiomarkerReading with measured_at timestamps

- **`build_clinical_snapshot(readings: list[BiomarkerReading]) -> ClinicalProfileSnapshot`**
  - Derives risk flags from biomarkers:
    - `high_hba1c`: if >= 6.5
    - `high_ldl`: if >= 3.4
    - `high_bp`: if systolic >= 140 or diastolic >= 90
  - Returns ClinicalProfileSnapshot with biomarkers dict and risk_flags list

### 3.2 Service & Use Cases

#### `service.py` - Reports Service
**Exports**: `parse_report_for_session`

#### `use_cases.py` - Report Use Cases
- **`parse_report_for_session(*, context, user_id, payload, request_id, correlation_id) -> ReportParseResponse`**
  - Parses report text and extracts biomarkers
  - Builds clinical snapshot with risk flags
  - Summarizes symptom check-ins for 6-day window
  - Runs report parse workflow
  - Returns readings, snapshot, and symptom summary

---

## 4. Households Features Module (`features/households/`)

### 4.1 Domain Layer

#### `policies.py` - Access Control
- **`HouseholdMembershipStorePort`** (Protocol)
  - `get_member_role(household_id: str, user_id: str) -> str | None`
  - `list_members(household_id: str) -> list[dict[str, Any]]`

- **Exceptions**:
  - `HouseholdAccessNotFoundError`
  - `HouseholdAccessForbiddenError`

- **Functions**:
  - `ensure_household_member(household_store, *, household_id, user_id) -> str`: Returns role or raises
  - `ensure_household_owner(household_store, *, household_id, user_id) -> None`: Raises if not owner
  - `household_source_members(household_store, *, household_id) -> tuple[list[str], dict[str, str]]`: Returns user_ids and display_names

#### `ports.py` - Application Ports
| Protocol | Methods |
|----------|---------|
| `HouseholdStorePort` | `get_household_for_user`, `get_household_by_id`, `create_household`, `list_members`, `get_member_role`, `rename_household`, `create_invite`, `join_by_invite`, `remove_member` |
| `AuthStorePort` | `set_active_household_for_session` |
| `HouseholdContext` | Properties for `settings`, `stores`, `coordinator`, `household_store`, `auth_store` |

#### `schemas.py` - Pydantic Schemas
| Model | Fields |
|-------|--------|
| `HouseholdCreateRequest` | `name: str` |
| `HouseholdUpdateRequest` | `name: str` |
| `HouseholdResponse` | `household_id`, `name`, `owner_user_id`, `created_at` |
| `HouseholdMemberItem` | `user_id`, `display_name`, `role` (owner/member), `joined_at` |
| `HouseholdMembersResponse` | `members: list[HouseholdMemberItem]` |
| `HouseholdCareContextResponse` | `viewer_user_id`, `subject_user_id`, `household_id` |
| `HouseholdCareMembersResponse` | `viewer_user_id`, `household_id`, `members` |
| `HouseholdBundleResponse` | `household`, `members`, `active_household_id` |
| `HouseholdInviteResponseItem` | `invite_id`, `household_id`, `code`, `created_by_user_id`, `created_at`, `expires_at`, `max_uses`, `uses` |
| `HouseholdInviteCreateResponse` | `invite: HouseholdInviteResponseItem` |
| `HouseholdJoinRequest` | `code: str` |
| `HouseholdActiveUpdateRequest` | `household_id: str \| None` |
| `HouseholdLeaveResponse` | `ok: bool`, `left_household_id: str` |
| `HouseholdMemberRemoveResponse` | `ok: bool`, `removed_user_id: str` |
| `HouseholdCareProfileResponse` | `context`, `profile: HealthProfileResponseItem` |
| `HouseholdCareMealSummaryResponse` | `context`, `summary: MealDailySummaryResponse` |
| `HouseholdCareReminderListResponse` | `context`, `reminders`, `metrics` |

### 4.2 Use Cases

#### `use_cases.py` - Household Operations
**Exceptions**:
- `HouseholdAlreadyExistsError`
- `HouseholdNotFoundError`
- `HouseholdForbiddenError`
- `HouseholdInviteInvalidError`
- `HouseholdMembershipConflictError`
- `HouseholdOwnerLeaveForbiddenError`

**Lifecycle Functions**:
- `get_current_household_bundle(*, household_store, user_id) -> HouseholdBundle`
- `create_household_for_user(*, household_store, user_id, display_name, name) -> HouseholdBundle`
- `list_household_members_for_user(*, household_store, household_id, user_id) -> list[dict]`
- `create_household_invite_for_owner(*, household_store, household_id, user_id) -> dict`
- `join_household_by_code(*, household_store, code, user_id, display_name) -> HouseholdBundle`
- `remove_household_member_for_owner(*, household_store, household_id, actor_user_id, target_user_id) -> None`
- `leave_household_for_member(*, household_store, household_id, user_id) -> None`
- `rename_household_for_owner(*, household_store, household_id, actor_user_id, name) -> HouseholdBundle`
- `validate_active_household_for_user(*, household_store, household_id, user_id) -> str | None`

**Response Projectors**:
- `household_response(item) -> HouseholdResponse`
- `household_member_response(item) -> HouseholdMemberItem`
- `household_bundle_response(...) -> HouseholdBundleResponse`
- `household_invite_response(invite) -> HouseholdInviteResponseItem`

---

## 5. Recommendations Features Module (`features/recommendations/`)

### 5.1 Domain Layer

#### `domain/models.py` - Recommendation Models
- **`InteractionEventType`**: "viewed", "accepted", "dismissed", "swap_selected", "meal_logged_after_recommendation", "ignored"

- **`RecommendationOutput`** (Pydantic BaseModel)
  - `safe: bool`, `rationale: str`, `localized_advice: list[str]`
  - `blocked_reason: str | None`, `evidence: dict[str, float]`

- **`DailySuggestionItem`** (Pydantic BaseModel)
  - `slot: MealSlot`, `title: str`, `venue_type: str`
  - `why_it_fits: list[str]`, `caution_notes: list[str]`, `confidence: float`

- **`DailySuggestionBundle`** (Pydantic BaseModel)
  - `locale: str`, `generated_at: str`
  - `data_sources: dict[str, object]`, `warnings: list[str]`
  - `suggestions: dict[str, DailySuggestionItem]`

- **`MealCatalogItem`** (Pydantic BaseModel)
  - `meal_id: str`, `title: str`, `locale: str`, `slot: MealSlot`, `venue_type: str`
  - `cuisine_tags`, `ingredient_tags`, `preparation_tags`
  - `nutrition: Nutrition`, `price_tier: Literal["budget", "moderate", "flexible"]`
  - `health_tags: list[str]`, `active: bool`

- **`RecommendationInteraction`** (Pydantic BaseModel)
  - `interaction_id: str`, `user_id: str`, `recommendation_id: str`, `candidate_id: str`
  - `event_type: InteractionEventType`, `slot: MealSlot`
  - `source_meal_id: str | None`, `selected_meal_id: str | None`
  - `created_at: datetime`, `metadata: dict[str, object]`

- **`PreferenceSnapshot`** (Pydantic BaseModel)
  - `user_id: str`, `updated_at: datetime`, `interaction_count: int`
  - `accepted_count: int`, `dismissed_count: int`, `swap_selected_count: int`
  - `cuisine_affinity: dict[str, float]`, `ingredient_affinity: dict[str, float]`
  - `health_tag_affinity: dict[str, float]`, `slot_affinity: dict[str, float]`
  - `substitution_tolerance: float = 0.6`, `adherence_bias: float = 0.0`

- **`CandidateScores`** (Pydantic BaseModel)
  - `preference_fit: float`, `temporal_fit: float`, `adherence_likelihood: float`
  - `health_gain: float`, `substitution_deviation_penalty: float`, `total_score: float`

- **`HealthDelta`** (Pydantic BaseModel)
  - `calories: float`, `sugar_g: float`, `sodium_mg: float`

- **`AgentRecommendationCard`** (Pydantic BaseModel)
  - `candidate_id: str`, `slot: MealSlot`, `title: str`, `venue_type: str`
  - `why_it_fits: list[str]`, `caution_notes: list[str]`, `confidence: float`
  - `scores: CandidateScores`, `health_gain_summary: HealthDelta`

- **`SubstitutionAlternative`** (Pydantic BaseModel)
  - `candidate_id: str`, `title: str`, `venue_type: str`
  - `health_delta: HealthDelta`, `taste_distance: float`, `reasoning: str`, `confidence: float`

- **`SubstitutionPlan`** (Pydantic BaseModel)
  - `source_meal: SourceMealSummary`
  - `alternatives: list[SubstitutionAlternative]`
  - `blocked_reason: str | None`

- **`TemporalContext`** (Pydantic BaseModel)
  - `current_slot: MealSlot`, `generated_at: datetime`
  - `meal_history_count: int`, `interaction_count: int`
  - `recent_repeat_titles: list[str]`, `slot_history_counts: dict[str, int]`

- **`AgentProfileState`** (Pydantic BaseModel)
  - `completeness_state: str`, `bmi: float | None`
  - `target_calories_per_day: float | None`, `macro_focus: list[str]`

- **`DailyAgentRecommendation`** (Pydantic BaseModel)
  - `profile_state: AgentProfileState`, `temporal_context: TemporalContext`
  - `recommendations: dict[str, AgentRecommendationCard]`
  - `substitutions: SubstitutionPlan | None`, `fallback_mode: bool`
  - `data_sources: dict[str, object]`, `constraints_applied: list[str]`

- **`CanonicalFoodAdvice`** (Pydantic BaseModel)
  - `cn: str | None`, `en: str`, `risk_level: str | None`

- **`CanonicalFoodAlternative`** (Pydantic BaseModel)
  - `name_en: str`, `name_cn: str | None`, `benefit: str`

- **`CanonicalFoodRecord`** (Pydantic BaseModel)
  - Comprehensive food record with nutrition, tags, disease advice, alternatives
  - Properties: `meal_id` (alias for `food_id`)

#### `domain/schemas.py` - Agent Schemas
- **`RecommendationAgentInput`** (Pydantic BaseModel)
  - `user_id: str`, `health_profile: HealthProfileRecord`
  - `user_profile: UserProfile`, `meal_history: list[MealRecognitionRecord]`
  - `clinical_snapshot: ClinicalProfileSnapshot | None`

- **`RecommendationAgentOutput`** (Pydantic BaseModel)
  - `recommendation: DailyAgentRecommendation`

#### `domain/canonical_food_matching.py` - Food Matching
**Functions**:
- `normalize_text(value: str) -> str`: Lowercases and tokenizes
- `build_default_canonical_food_records() -> list[CanonicalFoodRecord]`: Merges all seed sources
- `rank_food_candidates(*, records, locale, observed_label, candidate_aliases=None, detected_components=None, preparation=None) -> list[tuple[CanonicalFoodRecord, float]]`
  - Ranks records against observed label using name overlap and ingredients
  - Name score: 1.0 (exact), 0.82 (substring), 0.7 (token overlap)
  - Component/preparation/token scores weighted additively
- `find_food_by_name(records, name, *, locale="en-SG") -> CanonicalFoodRecord | None`
  - Returns best match above 0.5 threshold

#### `domain/context.py` - Temporal Context & Preferences
**Functions**:
- `build_temporal_context(*, meal_history, interaction_count) -> TemporalContext`
  - Counts meals per slot, tracks recent repeat titles

- `_apply_affinity_update(snapshot, *, candidate, event_type, weight=None) -> PreferenceSnapshot`
  - Updates cuisine/ingredient/health_tag/slot affinities
  - Adjusts substitution tolerance based on event type

- `_snapshot_from_history(*, repository, user_id, meal_history, catalog) -> PreferenceSnapshot`
  - Initializes snapshot from meal history

- `_ensure_snapshot(*, repository, user_id, meal_history, catalog) -> PreferenceSnapshot`
  - Gets or creates preference snapshot

#### `domain/engine.py` - Recommendation Engine
**Class: `RecommendationAgentRepository`** (Protocol)
- `list_canonical_foods(*, locale, slot=None, limit=100) -> list[FoodItem]`
- `get_preference_snapshot(user_id) -> PreferenceSnapshot | None`
- `save_preference_snapshot(snapshot) -> PreferenceSnapshot`
- `get_meal_record(user_id, meal_id) -> MealRecognitionRecord | None`
- `get_canonical_food(food_id) -> FoodItem | None`
- `find_food_by_name(*, locale, name) -> FoodItem | None`
- `save_recommendation_interaction(interaction) -> RecommendationInteraction`

**Constants**:
- `MEAL_LOG_WARMUP_THRESHOLD = 10`
- `INTERACTION_WARMUP_THRESHOLD = 5`

**Functions**:
- `generate_daily_agent_recommendation(*, repository, user_id, health_profile, user_profile, meal_history, clinical_snapshot) -> DailyAgentRecommendation`
  - Generates recommendations for all meal slots
  - Ranks candidates with multi-factor scoring
  - Returns with substitution plans

- `build_substitution_plan(*, repository, user_id, health_profile, user_profile, meal_history, clinical_snapshot, source_meal_id, limit) -> SubstitutionPlan | None`
  - Generates healthier low-deviation alternatives for source meal
  - Filters by health delta and taste distance

- `record_interaction_and_update_preferences(*, repository, user_id, candidate_id, recommendation_id, event_type, slot, source_meal_id, selected_meal_id, metadata, meal_history) -> tuple[RecommendationInteraction, PreferenceSnapshot]`
  - Logs user interaction with recommendation
  - Updates preference snapshot with affinity weights

#### `domain/meal_catalog_queries.py` - Meal Catalog
**Constant**: `DEFAULT_MEAL_CATALOG` - Tuple of 11 pre-built Singapore hawker MealCatalogItem records

**Functions**:
- `list_default_catalog(*, locale="en-SG") -> list[MealCatalogItem]`
- `find_catalog_item_by_title(title, *, locale="en-SG") -> MealCatalogItem | None`

#### `domain/meal_recommendations.py` - Meal Recommendations
**Constants**:
- `LOCAL_DISH_ALTERNATIVES`: Dict mapping dish names to advice (e.g., laksa -> ["Try fish soup with brown rice", ...])

**Functions**:
- `_local_advice_for_dish(dish_name, user_profile, clinical_snapshot) -> list[str]`
  - Generates localized advice based on dish, profile, and biomarkers

- `generate_recommendation(meal_record, clinical_snapshot, user_profile) -> RecommendationOutput`
  - Validates meal with SafetyEngine
  - Returns RecommendationOutput with safe flag, rationale, advice
  - Raises SafetyViolation → returns blocked_reason if triggered

#### `domain/scoring.py` - Scoring Functions
**Type aliases**:
- `FoodItem = CanonicalFoodRecord`

**Functions**:
- `_clamp(value, low=0.0, high=1.0) -> float`
- `_infer_slot(captured_at: datetime) -> MealSlot`: Based on hour (5-11: breakfast, 11-16: lunch, 16-22: dinner, else snack)
- `_score_similarity(candidate: FoodItem, record: MealRecognitionRecord | FoodItem) -> float`: 0-1 overlap score
- `_preference_fit(snapshot: PreferenceSnapshot, candidate: FoodItem) -> float`: Sigmoid of affinity averages
- `_temporal_fit(candidate, *, temporal, meal_history) -> tuple[float, list[str]]`: Slot matching + recency penalty
- `_health_gain(candidate, *, slot, meal_history, snapshot, profile) -> tuple[float, HealthDelta, list[str]]`: Nutrient improvements vs baseline + clinical bonuses
- `_adherence_likelihood(snapshot, *, preference_fit, temporal_fit) -> float`: Weighted combination with behavior signal
- `_candidate_constraints(candidate, *, profile, restricted_terms) -> tuple[bool, list[str], list[str]]`: Returns (allowed, constraint_codes, caution_notes)

**Dataclass**:
- **`RankedCandidate`**
  - `item: FoodItem`, `scores: CandidateScores`, `reasons: list[str]`
  - `caution_notes: list[str]`, `delta: HealthDelta`

### 5.2 Application Layer

#### `daily_suggestions.py` - Daily Suggestions
**Dataclass**: **`MealCandidate`** (frozen)
- `slot: str`, `title: str`, `venue_type: str`
- `cuisines: tuple[str, ...]`, `traits: tuple[str, ...]`
- `ingredients: tuple[str, ...]`, `caution_notes: tuple[str, ...]`

**Constant**: `SINGAPORE_CANDIDATES` - 7 pre-built meal candidates for breakfast/lunch/dinner/snack

**Functions**:
- `build_daily_suggestions(*, health_profile, user_profile, meal_history, biomarker_history, fallback_mode) -> DailySuggestionBundle`
  - Scores candidates against profile and clinical snapshot
  - Returns bundle with warnings and per-slot suggestions

#### `ports.py` - Recommendation Ports
| Protocol | Methods |
|----------|---------|
| `SuggestionRepositoryPort` | `list_meal_records`, `save_biomarker_readings`, `save_recommendation`, `save_suggestion_record`, `list_suggestion_records`, `get_suggestion_record` |
| `ClinicalMemoryPort` | `put(user_id, snapshot)` |
| `EventTimelinePort` | `append(event_type, correlation_id, payload, ...)` |
| `HouseholdStorePort` | `get_member_role`, `list_members` |

#### `service.py` - Recommendations Service
**Exports**: All public functions from use_cases and suggestion_session

#### `suggestion_session.py` - Session-Scoped Orchestration
**Functions**:
- `generate_from_report(*, context, session, payload, request_id, correlation_id) -> SuggestionGenerateFromReportResponse`
- `list_for_session(*, context, session, scope, limit, source_user_id) -> SuggestionListResponse`
- `get_for_session(*, context, session, scope, suggestion_id) -> SuggestionDetailResponse`

#### `use_cases.py` - Recommendation Use Cases
**Exceptions**:
- `NoMealRecordsError`
- `MissingActiveHouseholdError`
- `SuggestionForbiddenError`
- `SuggestionNotFoundError`

**Functions**:
- `generate_suggestion_from_report(*, repository, clinical_memory, session, text, request_id, correlation_id, build_user_profile, event_timeline) -> dict[str, Any]`
  - Parses text-based suggestions with safety evaluation
  - Handles household scope delegation

- `generate_recommendation_for_session(*, deps, session, meal_id, request_id, correlation_id) -> RecommendationGenerateResponse`
  - Single-meal recommendation with clinical context

- `generate_suggestion_from_report(...) -> dict[str, Any]` (internal use case)

- `get_daily_agent_for_session(*, deps, session) -> RecommendationAgentResponse`
  - Generates full daily recommendation bundle

- `get_substitutions_for_session(*, deps, user_id, meal_id) -> RecommendationSubstitutionResponse`
  - Builds substitution plan for specific meal

- `get_suggestion_for_session(*, repository, household_store, session, scope, suggestion_id) -> dict[str, Any]`

- `list_suggestions_for_session(*, repository, household_store, session, scope, limit, source_user_id) -> list[dict[str, Any]]`

- `record_interaction_for_session(*, deps, user_id, payload) -> RecommendationInteractionResponse`
  - Logs user interaction (accepted, dismissed, etc.) and updates preferences

---

## Summary Table: Key Exported Symbols

| Module | Key Classes/Functions | Purpose |
|--------|----------------------|---------|
| **safety** | `SafetyEngine`, `SafetyViolation`, `DrugInteractionDB` | Medical contraindication validation |
| **reminders** | `ReminderEvent`, `ReminderService`, `dispatch_reminder`, `materialize_reminder_notifications` | Medication/mobility reminders with multi-channel delivery |
| **reports** | `parse_report_input`, `build_clinical_snapshot` | Biomarker extraction and clinical risk assessment |
| **households** | `ensure_household_member`, `create_household_for_user`, `join_household_by_code` | Multi-user household management |
| **recommendations** | `generate_daily_agent_recommendation`, `build_substitution_plan`, `rank_food_candidates` | AI-driven personalized meal recommendations |

---

## Architecture Patterns

1. **Domain-Driven Design**: Each feature has a clear `domain/` layer with pure business logic
2. **Hex Architecture**: Ports and protocols decouple domain from infrastructure
3. **Outbox Pattern**: Reminders use SQLite outbox for reliable event delivery
4. **Multi-Factor Scoring**: Recommendations combine preference fit + temporal fit + health gain + adherence
5. **Clinical Context**: Safety and recommendations integrate biomarker snapshots for personalized guidance
6. **Household Scoping**: All recommendation and reminder operations support both self and household scopes

---

**Documentation Complete** — All 40+ files documented with comprehensive class/method/function signatures and behavior descriptions.