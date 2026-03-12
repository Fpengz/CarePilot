# Dietary Guardian Platform Module Reference

## Module Overview

The platform layer provides foundational services for authentication, caching, messaging, observability, and storage. This documentation covers all exported symbols, classes, and methods across these subsystems.

---

## 1. Authentication Platform (`platform/auth/`)

### 1.1 `demo_defaults.py`

**Purpose**: Builds demo user seeds for testing and development environments.

| Symbol | Type | Description |
|--------|------|-------------|
| `DemoUserSeed` | Type Alias | `tuple[str, str, str, AccountRole, ProfileMode, str]` – (user_id, email, display_name, account_role, profile_mode, password) |
| `build_demo_user_seeds(settings: Settings)` | Function | Returns list of demo user seeds with credentials from settings; includes member, helper, and admin accounts |

---

### 1.2 `in_memory.py`

**Purpose**: In-memory authentication store with PBKDF2 password hashing, session management, login failure tracking, and audit logging.

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `AuthUserRecord` | N/A | @dataclass | Represents an authenticated user: `user_id`, `email`, `display_name`, `account_role`, `profile_mode`, `password_hash` |
| `PasswordHasher` | `__init__(scheme: str)` | Constructor | Initializes hasher with scheme (only "pbkdf2_sha256" supported) |
| | `hash(password: str)` | Method | Returns PBKDF2-SHA256 hashed password with salt and iterations |
| | `verify(password: str, encoded: str)` | Method | Verifies password against stored hash; returns bool |
| `InMemoryAuthStore` | `__init__(settings: Settings)` | Constructor | Initializes in-memory store with session TTL, login attempt limits; seeds demo users if enabled |
| | `authenticate(email: str, password: str)` | Method | Returns `AuthUserRecord` if credentials valid, else None |
| | `create_user(email, password, display_name, account_role="member", profile_mode="self")` | Method | Creates new user; returns `AuthUserRecord` or None on duplicate email |
| | `is_login_locked(email: str)` | Method | Checks if email is in lockout window; auto-unlocks if window expired |
| | `record_login_failure(email: str)` | Method | Increments failure counter; returns True if lockout triggered |
| | `record_login_success(email: str)` | Method | Clears failure tracking for email |
| | `append_auth_audit_event(event_type, email, user_id=None, metadata=None)` | Method | Appends timestamped audit event with bounded circular buffer |
| | `list_auth_audit_events(limit: int = 50)` | Method | Returns up to `limit` audit events (max 200) in reverse chronological order |
| | `update_user_profile(user_id, display_name=None, profile_mode=None)` | Method | Updates user profile and syncs to active sessions |
| | `change_user_password(user_id, current_password, new_password, keep_session_id)` | Method | Changes password; revokes all other sessions; returns `(success: bool, revoked_count: int)` |
| | `create_session(user: AuthUserRecord)` | Method | Creates new session dict with `session_id`, user info, scopes, issued_at |
| | `get_session(session_id: str)` | Method | Retrieves session; auto-destroys if expired; returns dict or None |
| | `destroy_session(session_id: str)` | Method | Removes session by ID |
| | `list_sessions_for_user(user_id: str)` | Method | Returns valid sessions for user, sorted by issued_at descending |
| | `get_session_owner(session_id: str)` | Method | Returns user_id owning session or None |
| | `revoke_other_sessions(user_id, keep_session_id: str)` | Method | Destroys all sessions except keep_session_id; returns count revoked |
| | `set_active_household_for_session(session_id, active_household_id: str\|None)` | Method | Updates active household; returns updated session or None |
| | `close()` | Method | No-op cleanup |

**Helper Functions**:
- `_pbkdf2_hash(password: str, salt: bytes\|None = None)` → `str`: PBKDF2-SHA256 with 200k iterations
- `_pbkdf2_verify(password: str, encoded: str)` → `bool`: Constant-time verification

---

### 1.3 `ports.py`

**Purpose**: Protocol definitions for auth store adapters.

| Protocol | Methods |
|----------|---------|
| `AuthStorePort` | `is_login_locked(email: str)` → bool |
| | `authenticate(email: str, password: str)` → `AuthUserRecord \| None` |
| | `record_login_failure(email: str)` → bool |
| | `record_login_success(email: str)` → None |
| | `append_auth_audit_event(event_type, email, user_id=None, metadata=None)` → None |
| | `create_session(user: AuthUserRecord)` → dict[str, Any] |
| | `create_user(email, password, display_name, account_role="member", profile_mode="self")` → `AuthUserRecord \| None` |

---

### 1.4 `session_context.py`

**Purpose**: Builds `UserProfile` from session state with optional health profile repository lookup.

| Function | Signature | Description |
|----------|-----------|-------------|
| `build_user_profile_from_session(session: dict[str, Any], repository: HealthProfileRepository\|None = None)` | Function | Creates UserProfile by merging session data with health profile; applies default profile mode if not in session |

---

### 1.5 `session_signer.py`

**Purpose**: Session token signing/verification using itsdangerous.

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `SessionSigner` | `__init__(secret: str)` | Constructor | Creates URLSafeTimedSerializer with salt "dietary-guardian-session" |
| | `sign(session_id: str)` | Method | Returns signed token containing session_id |
| | `unsign(token: str, max_age_seconds: int)` | Method | Extracts session_id from token if valid and not expired; returns str or None |

---

### 1.6 `sqlite_store.py` (excerpt)

**Purpose**: Persistent SQLite-backed authentication store mirroring in-memory API.

| Class | Method | Description |
|-------|--------|-------------|
| `SQLiteAuthStore` | Mirrors `InMemoryAuthStore` | Implements same `AuthStorePort` protocol with SQLite persistence. Tables: `auth_users`, `auth_sessions`, `auth_login_failures`, `auth_audit_events`. Uses RLock for thread safety. |

**Schema**:
- `auth_users`: user_id (PK), email (UNIQUE), display_name, account_role, profile_mode, password_hash, created_at
- `auth_sessions`: session_id (PK), user_id, email, account_role, profile_mode, scopes_json, display_name, issued_at, subject_user_id, active_household_id
- `auth_login_failures`: email (PK), failed_count, window_started_at, lockout_until
- `auth_audit_events`: event_id (PK), event_type, email, user_id, created_at, metadata_json (with index on created_at DESC)

---

### 1.7 `use_cases.py`

**Purpose**: High-level authentication use cases (login, signup, session creation).

| Exception | Description |
|-----------|-------------|
| `LoginLockedError` | Raised when login attempt made during lockout window |
| `InvalidCredentialsError` | Raised on failed authentication |
| `DuplicateEmailError` | Raised when signup attempts existing email |
| `InvalidSignupPasswordError` | Raised when password < 12 chars |

| Class/Function | Signature | Description |
|---|---|---|
| `AuthSessionResult` | @dataclass | Contains `user: AuthUserRecord` and `session: dict[str, Any]` |
| `login_and_create_session(auth_store: AuthStorePort, email: str, password: str)` | Function | Authenticates, checks lockout, records success/failure, appends audit event; raises LoginLockedError or InvalidCredentialsError |
| `signup_member_and_create_session(auth_store: AuthStorePort, email: str, password: str, display_name: str, profile_mode: ProfileMode)` | Function | Creates new member account with profile_mode; validates password ≥ 12 chars; appends signup_success audit event; raises DuplicateEmailError or InvalidSignupPasswordError |
| `MIN_PASSWORD_LENGTH` | Constant = 12 | Minimum signup password length |

---

## 2. Caching Platform (`platform/cache/`)

### 2.1 `clinical_snapshot_cache.py`

**Purpose**: In-process memory cache for `ClinicalProfileSnapshot` objects keyed by user_id.

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `ClinicalSnapshotMemoryService` | `__init__()` | Constructor | Thread-unsafe in-process cache |
| | `put(user_id: str, snapshot: ClinicalProfileSnapshot)` | Method | Stores snapshot by user_id; logs at INFO level |
| | `get(user_id: str)` | Method | Retrieves snapshot or None |

---

### 2.2 `in_memory.py`

**Purpose**: Thread-safe in-memory cache store with TTL support.

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `InMemoryCacheStore` | `__init__()` | Constructor | Uses dict and Lock for thread safety |
| | `get_json(key: str)` | Method | Returns cached value or None; auto-deletes if expired |
| | `set_json(key: str, value: Any, ttl_seconds: int\|None = None)` | Method | Stores value with optional TTL; None = no expiration |
| | `delete(key: str)` | Method | Removes key from cache |
| | `close()` | Method | No-op cleanup |

---

### 2.3 `profile_cache.py`

**Purpose**: In-process memory cache for `UserProfile` objects.

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `ProfileMemoryService` | `__init__()` | Constructor | Thread-unsafe in-process cache |
| | `put(profile: UserProfile)` | Method | Stores profile by profile.id; logs at INFO level |
| | `get(user_id: str)` | Method | Retrieves profile or None |

---

### 2.4 `rate_limiter.py`

**Purpose**: Token-bucket rate limiting with in-memory and Redis backends.

| Protocol | Method | Signature |
|----------|--------|-----------|
| `RateLimiter` | `allow(key: str, limit: int, window_seconds: int)` | Returns `(allowed: bool, retry_after_seconds: int)` |

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `InMemoryRateLimiter` | `__init__()` | Constructor | Uses deque per key with Lock |
| | `allow(key, limit, window_seconds)` | Method | Token-bucket: increments counter, prunes expired, checks limit; returns (bool, retry_after_sec) |
| `RedisRateLimiter` | `__init__(redis_url, namespace)` | Constructor | Connects to Redis with namespace |
| | `allow(key, limit, window_seconds)` | Method | Uses Redis INCR+TTL with pipelining |
| | `close()` | Method | Closes Redis client |
| `build_rate_limiter(settings: Settings)` | Function | Factory: returns Redis limiter if configured, else in-memory |

---

### 2.5 `redis_store.py`

**Purpose**: Redis-backed cache with domain-based key partitioning.

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `RedisCacheStore` | `__init__(redis_url: str, namespace: str)` | Constructor | Connects to Redis, parses namespace |
| | `_domain(key: str)` | Method | Categorizes key by content ("reminder", "notification", "workflow"/"outbox", else "general") |
| | `_key(key: str)` | Method | Returns namespaced key: `{namespace}:cache:{domain}:{key}` |
| | `get_json(key: str)` | Method | Returns JSON-deserialized value or None |
| | `set_json(key, value, ttl_seconds=None)` | Method | Stores JSON with optional expiry |
| | `delete(key: str)` | Method | Removes key |
| | `close()` | Method | Closes Redis client |
| `_load_redis_module()` | Function | Imports redis package or raises RuntimeError |

---

### 2.6 `timeline_service.py`

**Purpose**: Append-only event timeline with optional durable persistence for workflow tracing.

| Protocol | Method | Signature |
|----------|--------|-----------|
| `WorkflowTimelineRepository` | `save_workflow_timeline_event(event: WorkflowTimelineEvent)` | Returns persisted event |
| | `list_workflow_timeline_events(correlation_id=None, user_id=None)` | Returns list of events |

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `EventTimelineService` | `__init__(repository=None, persistence_enabled=False)` | Constructor | In-memory events list + optional repository |
| | `append(event_type, correlation_id, payload, request_id=None, user_id=None, workflow_name=None)` | Method | Creates `WorkflowTimelineEvent`, appends to in-memory list, optionally persists; returns event |
| | `get_events(correlation_id=None, user_id=None)` | Method | Queries in-memory or repository; filters by correlation_id/user_id; returns sorted by created_at |

---

## 3. Messaging Platform (`platform/messaging/`)

### 3.1 `alert_outbox.py`

**Purpose**: Alert publishing and outbox worker with retry/dead-letter semantics.

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `AlertPublisher` | `__init__(repository: AlertRepositoryProtocol)` | Constructor | Wraps repository |
| | `publish(message: AlertMessage)` | Method | Enqueues alert in repository; logs publishing event; returns list[OutboxRecord] |
| `OutboxWorker` | `__init__(repository, lease_owner="worker-1", max_attempts=3, concurrency=4)` | Constructor | Initializes sink adapters (in_app, push, email, sms, telegram, whatsapp, wechat) |
| | `process_once(alert_id=None)` | Async Method | Leases up to `concurrency` records, delivers concurrently; returns list[AlertDeliveryResult] |
| | `_deliver_record(record: OutboxRecord)` | Async Method | Routes to sink; handles success/retry/dead-letter; logs delivery events |
| | `_sync_reminder_notification_processing(record, attempt)` | Method | Syncs reminder notification state if type is "reminder_notification" |
| | `_sync_reminder_notification_delivered(record, attempt)` | Method | Marks scheduled notification delivered |
| | `_sync_reminder_notification_retry(record, attempt, next_attempt_at, error)` | Method | Reschedules notification with exponential backoff |
| | `_sync_reminder_notification_dead_letter(record, attempt, error)` | Method | Marks notification dead-lettered |

**Exported**:
- `AlertPublisher`, `AlertRepositoryProtocol`, `EmailSink`, `InAppSink`, `OutboxWorker`, `PushSink`, `SmsSink`, `SinkAdapter`, `TelegramSink`, `WeChatSink`, `WhatsAppSink`

---

### 3.2 `channels/base.py`

**Purpose**: Channel adapter protocols and shared result model.

| Model | Fields | Description |
|-------|--------|-------------|
| `ChannelResult` | channel: str, success: bool, attempts: int = 1, error: str\|None, delivered_at: datetime\|None, destination: str\|None | Pydantic model for channel delivery outcome |

| Protocol | Property/Method | Signature |
|----------|---|---|
| `NotificationChannel` | `name` | str |
| | `send(reminder_event: ReminderEvent)` | → ChannelResult |
| `SinkAdapter` | `name` | str |
| | `send(message: AlertMessage)` | → AlertDeliveryResult |

---

### 3.3 `channels/sinks.py`

**Purpose**: Concrete outbox sink implementations (in_app, push, email, SMS, telegram, whatsapp, wechat).

| Class | Attributes | Methods | Description |
|-------|-----------|---------|-------------|
| `InAppSink` | `name = "in_app"` | `send(message)` | Returns success=True with destination "app://alerts" |
| `PushSink` | `name = "push"` | `send(message)` | Returns success=True with destination "push://default" |
| `EmailSink` | `name = "email"` | `send(message)` | SMTP delivery; checks dev_mode, destination, config; handles TLS/auth |
| `SmsSink` | `name = "sms"` | `send(message)` | HTTP webhook delivery; checks dev_mode, destination, config |
| `TelegramSink` | `name = "telegram"` | `__init__()`, `send(message)` | Adapts alert to `ReminderEvent`, delegates to `TelegramChannel` |
| `WhatsAppSink` | `name = "whatsapp"` | `__init__()`, `send(message)` | Adapts alert to `ReminderEvent`, delegates to `WhatsAppChannel` |
| `WeChatSink` | `name = "wechat"` | `__init__()`, `send(message)` | Adapts alert to `ReminderEvent`, delegates to `WeChatChannel` |

**Helper**:
- `_alert_to_reminder(message: AlertMessage)` → `ReminderEvent`: Converts AlertMessage to ReminderEvent for channel adapters

---

### 3.4 `channels/telegram.py`

**Purpose**: Telegram bot adapter for reminder notifications.

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `TelegramChannel` | `__init__()` | Constructor | Loads config (bot_token, chat_id, dev_mode, timezone, request_timeout) |
| | `_build_endpoint()` | Method | Returns Telegram API sendMessage URL |
| | `_format_scheduled_at(value: datetime)` | Method | Formats datetime to local timezone ISO format |
| | `_build_payload(reminder_event: ReminderEvent)` | Method | Builds `{chat_id, text}` JSON payload |
| | `send(reminder_event: ReminderEvent)` | Method | POSTs to Telegram API or skips in dev_mode; returns ChannelResult |

---

### 3.5 `channels/wechat.py`

**Purpose**: WeChat adapter stub (placeholder for WeChat API integration).

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `WeChatChannel` | `send(reminder_event: ReminderEvent)` | Method | Stub implementation; logs and returns success=True with destination "wechat://stub" |

---

### 3.6 `channels/whatsapp.py`

**Purpose**: WhatsApp adapter stub (placeholder for Twilio/Meta API integration).

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `WhatsAppChannel` | `send(reminder_event: ReminderEvent)` | Method | Stub implementation; logs and returns success=True with destination "whatsapp://stub" |

---

### 3.7 `message_composer.py`

**Purpose**: Message formatting for alerts tailored to channel capabilities.

| Model | Fields | Description |
|-------|--------|-------------|
| `ChannelCapability` | channel: str, supports_text: bool = True, supports_images: bool = False, supports_buttons: bool = False, max_chars: int = 4096, rate_limit_hint: str\|None | Channel transport capabilities |

| Constant | Value | Description |
|----------|-------|-------------|
| `CHANNEL_CAPABILITIES` | dict[str, ChannelCapability] | Pre-configured capabilities for in_app, push, telegram, whatsapp, wechat |

| Function | Signature | Description |
|----------|-----------|-------------|
| `compose_alert_message(alert: AlertMessage, channel: str)` | Function | Builds `PresentationMessage` from alert; titles by alert.type; body includes medication/dosage if reminder |
| `format_alert_text_for_transport(message: PresentationMessage)` | Function | Renders to plain string: "{title}: {body}" |

---

## 4. Observability Platform (`platform/observability/`)

### 4.1 `context.py`

**Purpose**: Context-local correlation and request ID tracking using contextvars.

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_correlation_id()` | Function | Returns current correlation_id from context or None |
| `get_request_id()` | Function | Returns current request_id from context or None |
| `current_observability_context()` | Function | Returns dict with correlation_id and request_id if set |
| `bind_observability_context(correlation_id=None, request_id=None)` | Context Manager | Sets context vars; resets on exit |

---

### 4.2 `diagnostics/readiness.py`

**Purpose**: System readiness diagnostic report for `/health/ready` endpoint.

| TypedDict | Fields | Description |
|-----------|--------|-------------|
| `ReadinessCheck` | name: str, status: str, required: bool, detail: str | Single check result |
| `ReadinessReport` | status: str, checks: list[ReadinessCheck], warnings: list[str], errors: list[str] | Overall readiness report |

| Function | Signature | Description |
|----------|-----------|-------------|
| `build_readiness_report(settings: Settings)` | Function | Performs checks: app_env, required_provider, durable_storage, redis_url, redis_connectivity, shared_rate_limiting, email/sms/telegram configuration; returns report |
| `_check(name, status, required, detail)` | Helper | Returns ReadinessCheck dict |
| `_try_redis_ping(redis_url: str)` | Helper | Attempts Redis ping; returns (bool, str) result |

---

### 4.3 `logging.py`

**Purpose**: Structured logging and observability span context management.

| Function | Signature | Description |
|----------|-----------|-------------|
| `log_event(logger, level, event, **fields)` | Function | Logs event with merged observability context and kwargs |
| `observability_span(name, **context)` | Context Manager | Binds correlation_id/request_id from context dict |

**Imported from setup**: `get_logger`, `logger`, `setup_logging`

---

### 4.4 `setup.py`

**Purpose**: Logfire and logging initialization.

| Function | Signature | Description |
|----------|-----------|-------------|
| `setup_logging(project_name="dietary-guardian")` | Function | Initializes root logger with logfire handler, resolves log level from settings, dedupes handlers; returns logger |
| `get_logger(name: str)` | Function | Calls setup_logging then returns logger by name |
| `_resolve_log_level_name()` | Helper | Reads DIETARY_GUARDIAN_LOG_LEVEL or settings.observability.log_level |
| `_has_logfire_handler()` | Helper | Checks root handlers for logfire |
| `_dedupe_logfire_handlers()` | Helper | Removes duplicate logfire handlers |

**Globals**:
- `logger`: Root dietary-guardian logger

---

### 4.5 `tooling/domain/authorization.py`

**Purpose**: Authorization scopes for account roles.

| Constant | Value | Description |
|----------|-------|-------------|
| `MEMBER_SCOPES` | set[str] | {meal:write, meal:read, report:write, report:read, recommendation:generate, reminder:write, reminder:read, emotion:infer} |
| `ADMIN_EXTRA_SCOPES` | set[str] | {alert:trigger, alert:timeline:read, workflow:read, workflow:replay, workflow:write, auth:audit:read} |

| Function | Signature | Description |
|----------|-----------|-------------|
| `scopes_for_account_role(account_role: AccountRole)` | Function | Returns sorted list of scopes for role (member or admin) |
| `has_scopes(current_scopes: list[str], required_scopes: set[str])` | Function | Returns bool: required_scopes ⊆ current_scopes |
| `default_profile_mode_for_role(account_role: AccountRole)` | Function | Returns "self" for all roles |

---

### 4.6 `tooling/domain/models.py`

**Purpose**: Data models for tool specifications, execution, and results.

| Enum | Values | Description |
|------|--------|-------------|
| `ToolErrorClass` | VALIDATION, POLICY_BLOCKED, UNAVAILABLE, TIMEOUT, RETRYABLE, INTERNAL, NOT_FOUND | Tool error classifications |
| `ToolSideEffect` | READ, MUTATE, EXTERNAL | Tool side effect types |
| `ToolSensitivity` | LOW, PHI, MEDICATION, NOTIFICATION | Data sensitivity levels |

| Pydantic Model | Fields | Description |
|---|---|---|
| `ToolPolicyContext` | account_role: str, scopes: list[str], environment: str = "dev", user_id: str\|None, correlation_id: str\|None | Execution context for tool policy checks |
| `ToolSpec` | name: str, purpose: str, input_schema: type[BaseModel], output_schema: type[BaseModel], required_scopes: list[str], allowed_environments: list[str], side_effect: ToolSideEffect, sensitivity: ToolSensitivity, timeout_seconds: int = 30, retryable: bool, idempotent: bool | Tool specification and metadata |
| `ToolExecutionError` | classification: ToolErrorClass, message: str, retryable: bool, details: dict[str, Any] | Error result detail |
| `ToolExecutionResult` | tool_name: str, success: bool, output: BaseModel\|None, error: ToolExecutionError\|None, latency_ms: float, trace_metadata: dict[str, str], executed_at: datetime | Tool execution outcome |

---

### 4.7 `tooling/domain/tool_policy.py`

**Purpose**: Tool policy evaluation for role-based authorization.

| TypedDict | Fields | Description |
|-----------|--------|-------------|
| `ToolPolicyEvaluation` | policy_mode: Literal["shadow", "enforce"], code_decision: Literal["allow", "deny"], db_decision: Literal["allow", "deny"]\|None, effective_decision: Literal["allow", "deny"], diverged: bool, matched_policy_id: str\|None | Policy evaluation result |

| Function | Signature | Description |
|----------|-----------|-------------|
| `create_tool_policy_record(role, agent_id, tool_name, effect, conditions=None, priority=0, enabled=True)` | Function | Creates `ToolRolePolicyRecord` with UUID id and current timestamp |
| `apply_tool_policy_patch(record: ToolRolePolicyRecord, patch: dict[str, object])` | Function | Returns patched record with updated effect/conditions/priority/enabled |
| `resolve_db_decision(policies, role, agent_id, tool_name, environment)` | Function | Finds matching policy with highest priority (deny > allow); returns (effect, matched_policy) |
| `evaluate_tool_policy(policies, role, agent_id, tool_name, environment, code_allows_tool, mode)` | Function | Compares code decision vs DB decision; returns `ToolPolicyEvaluation` |
| `_environment_match(policy, environment)` | Helper | Checks if policy's environment condition matches |

---

### 4.8 `tooling/platform_registry.py`

**Purpose**: Platform tool registry with pre-registered `trigger_alert` tool.

| Pydantic Model | Fields | Description |
|---|---|---|
| `TriggerAlertToolInput` | alert_type: str, severity: AlertSeverity, message: str, destinations: list[str] | Input schema |
| `TriggerAlertToolOutput` | alert_id: str, correlation_id: str, deliveries: list[dict[str, str\|int\|bool\|None]] | Output schema |

| Function | Signature | Description |
|----------|-----------|-------------|
| `build_platform_tool_registry(repository: AlertRepositoryProtocol)` | Function | Creates `ToolRegistry`, registers `trigger_alert` tool with EXTERNAL side-effect and NOTIFICATION sensitivity; returns registry |

---

### 4.9 `tooling/registry.py`

**Purpose**: Runtime tool registry with validation, dispatch, and metering.

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `ToolRegistry` | `__init__()` | Constructor | Initializes specs, handlers, metrics dicts |
| | `register(spec: ToolSpec, handler: Any)` | Method | Stores spec and handler; initializes metrics |
| | `list_specs()` | Method | Returns list of ToolSpec |
| | `execute(tool_name, payload, context: ToolPolicyContext)` | Method | Validates spec/handler, checks scopes and environment, validates input, calls handler, validates output; returns `ToolExecutionResult` with metrics |
| | `_record_metrics(tool_name, result)` | Method | Updates calls/success/failure/latency counters |
| | `snapshot_metrics()` | Method | Returns dict of tool metrics: calls, success, failure, avg_latency_ms |

---

### 4.10 `workflows/coordinator.py`

**Purpose**: Workflow orchestration for meal analysis, alerts, report parsing, and replay.

| Constant | Value | Description |
|----------|-------|-------------|
| `WORKFLOW_DEFINITIONS` | dict[WorkflowName, list[str]] | Agent step sequences for each workflow |

| Class | Method | Signature | Description |
|-------|--------|-----------|-------------|
| `WorkflowCoordinator` | `__init__(tool_registry, profile_memory, clinical_memory, event_timeline)` | Constructor | Stores services |
| | `run_meal_analysis_workflow(capture, vision_result, user_profile, meal_record_id=None)` | Method | Appends timeline events, builds output, creates handoffs, returns `WorkflowExecutionResult` |
| | `run_alert_workflow(user_profile, alert_type, severity, message, destinations, request_id=None, correlation_id=None, account_role="member", scopes=None, environment="dev")` | Method | Issues IDs, appends events, executes `trigger_alert` tool, creates handoff, returns result |
| | `run_report_parse_workflow(user_id, request_id, correlation_id, source, reading_count, symptom_checkin_count, red_flag_count, window)` | Method | Appends workflow started/completed events, returns result |
| | `replay_workflow(correlation_id)` | Method | Retrieves timeline events, returns replay result |

**Support Functions**:
- `policy_item_response(item: ToolRolePolicyRecord)` → ToolPolicyItemResponse
- `runtime_contract_hash(runtime)` → str: SHA256 of sorted JSON
- `snapshot_item_response(item: WorkflowContractSnapshotRecord)` → WorkflowSnapshotItemResponse
- `timeline_event_response(event: WorkflowTimelineEvent)` → WorkflowTimelineEventResponse
- `get_workflow(deps, correlation_id)` → WorkflowResponse: Replays workflow
- `list_workflows(deps)` → WorkflowListResponse: Lists workflows grouped by correlation_id
- `get_runtime_contract(deps)` → WorkflowRuntimeRegistryResponse: Exposes runtime contract

---

### 4.11 `workflows/domain/models.py`

**Purpose**: Domain models for workflows, tool policies, and timeline events.

| Type Alias | Definition | Description |
|---|---|---|
| `ToolPolicyEffect` | Literal["allow", "deny"] | Policy effect |

| Pydantic Model | Fields | Description |
|---|---|---|
| `ToolRolePolicyRecord` | id: str, role: AccountRole, agent_id: str, tool_name: str, effect: ToolPolicyEffect, conditions: dict, priority: int, enabled: bool, created_at: datetime, updated_at: datetime | Persisted tool policy |
| `WorkflowName` | StrEnum: MEAL_ANALYSIS, ALERT_ONLY, REPORT_PARSE, REPLAY | Workflow names |
| `WorkflowTimelineEvent` | event_id: str, event_type: str, workflow_name: str\|None, request_id: str\|None, correlation_id: str, user_id: str\|None, payload: dict, created_at: datetime | Timeline event |
| `WorkflowExecutionResult` | workflow_name: WorkflowName, request_id: str, correlation_id: str, user_id: str\|None, output_envelope: AgentOutputEnvelope\|None, handoffs: list[AgentHandoff], tool_results: list[ToolExecutionResult], timeline_events: list[WorkflowTimelineEvent], replayed: bool, created_at: datetime | Workflow execution outcome |
| `AgentContract` | agent_id: str, capabilities: list[str], allowed_tools: list[str], output_contract: str | Agent contract |
| `WorkflowRuntimeStep` | step_id: str, agent_id: str, capability: str, tool_names: list[str] | Single workflow step |
| `WorkflowRuntimeContract` | workflow_name: WorkflowName, steps: list[WorkflowRuntimeStep] | Workflow contract |
| `WorkflowContractSnapshotRecord` | id: str, version: int, contract_hash: str, source: WorkflowContractSnapshotSource, workflows: list[WorkflowRuntimeContract], agents: list[AgentContract], created_by: str\|None, created_at: datetime | Workflow contract snapshot |

| Type Alias | Definition | Description |
|---|---|---|
| `WorkflowContractSnapshotSource` | Literal["startup_bootstrap", "manual_api"] | Snapshot source |

---

## 5. Storage Platform (`platform/storage/`)

### 5.1 `media/ingestion.py`

**Purpose**: Media capture envelope building and deduplication.

| Function | Signature | Description |
|----------|-----------|-------------|
| `compute_content_sha256(payload: bytes)` | Function | Returns SHA256 hex digest of bytes |
| `build_capture_envelope(image_input: ImageInput, user_id=None, request_id=None, correlation_id=None)` | Function | Wraps ImageInput in CaptureEnvelope with generated IDs and content hash |
| `should_suppress_duplicate_capture(session_state, envelope, window_seconds=30, session_key="default")` | Function | Returns True if same image captured within window; stores hash timestamp in session |

---

### 5.2 `media/upload.py`

**Purpose**: Image upload preprocessing with MIME validation and optional downscaling.

| Protocol | Property/Method | Signature |
|----------|---|---|
| `UploadedFileLike` | `name` | str |
| | `type` | str |
| | `getvalue()` | → bytes |

| Constant | Value | Description |
|----------|-------|-------------|
| `SUPPORTED_IMAGE_TYPES` | {"image/jpeg", "image/png", "image/webp"} | Allowed MIME types |

| Function | Signature | Description |
|----------|-----------|-------------|
| `build_image_input(uploaded_file, camera_file, downscale_enabled=False, max_side_px=1024)` | Function | Validates MIME type, optionally downscales via Pillow, wraps as ImageInput; returns (ImageInput\|None, error_str\|None) |
| `_estimate_multi_item_count(filename)` | Helper | Heuristic: splits filename by underscore/hyphen; returns 1–4 |
| `_maybe_downscale_image(payload, mime_type, enabled, max_side_px)` | Helper | Returns (bytes, metadata_dict): downscales if > max_side_px using Lanczos; adds metadata |

---

## Summary

This reference documents **33 files** across the dietary_guardian platform layer:

- **Authentication** (7 files): In-memory and SQLite stores, session signing, audit logging, login lockout
- **Caching** (6 files): Profile/clinical snapshots, TTL-based stores, rate limiting, workflow timeline
- **Messaging** (7 files): Alert outbox/publishing, 7 channel adapters (in_app, push, email, SMS, Telegram, WhatsApp, WeChat)
- **Observability** (11 files): Context binding, logging, readiness checks, tool specs, policy evaluation, workflow coordination, timeline events
- **Storage** (2 files): Image upload validation, capture deduplication

All classes, methods, and functions are documented with signatures, parameters, return types, and descriptions for integration and testing.