# Database Schema (SQLModel)

_Generated from SQLModel metadata. Do not edit by hand._

- Generated: 2026-03-29
- Source: `src/care_pilot/platform/persistence/models`
- Command: `uv run python scripts/docs/generate_db_schema.py`

## Tables

### alert_outbox

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| alert_id | VARCHAR | False | True |
| sink | VARCHAR | False | True |
| type | VARCHAR | False | False |
| severity | VARCHAR | False | False |
| payload | JSON | True | False |
| correlation_id | VARCHAR | False | False |
| state | VARCHAR | False | False |
| attempt_count | INTEGER | False | False |
| next_attempt_at | DATETIME | False | False |
| last_error | VARCHAR | True | False |
| lease_owner | VARCHAR | True | False |
| lease_until | DATETIME | True | False |
| idempotency_key | VARCHAR | False | False |

### auth_login_failures

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| email | VARCHAR | False | True |
| failed_count | INTEGER | False | False |
| window_started_at | DATETIME | True | False |
| lockout_until | DATETIME | True | False |

### auth_users

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| user_id | VARCHAR | False | True |
| email | VARCHAR | False | False |
| display_name | VARCHAR | False | False |
| account_role | VARCHAR | False | False |
| profile_mode | VARCHAR | False | False |
| password_hash | VARCHAR | False | False |
| created_at | DATETIME | False | False |

### user_profiles

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | VARCHAR | False | True |
| name | VARCHAR | False | False |
| age | INTEGER | False | False |
| profile_mode | VARCHAR | False | False |
| locale | VARCHAR | False | False |
| allergies | JSON | True | False |
| budget_tier | VARCHAR | False | False |
| target_calories_per_day | FLOAT | True | False |
| daily_sodium_limit_mg | FLOAT | False | False |
| daily_sugar_limit_g | FLOAT | False | False |
| daily_protein_target_g | FLOAT | False | False |
| daily_fiber_target_g | FLOAT | False | False |

### accounts

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | VARCHAR | False | True |
| email | VARCHAR | False | False |
| password_hash | VARCHAR | False | False |
| display_name | VARCHAR | False | False |
| role | VARCHAR | False | False |
| profile_mode | VARCHAR | False | False |
| subject_user_id | VARCHAR | True | False |

### auth_audit_events

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| event_id | VARCHAR | False | True |
| user_id | VARCHAR | True | False |
| email | VARCHAR | False | False |
| event_type | VARCHAR | False | False |
| occurred_at | DATETIME | False | False |
| created_at | DATETIME | False | False |
| metadata_json | JSON | True | False |

### auth_sessions

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| session_id | VARCHAR | False | True |
| user_id | VARCHAR | False | False |
| email | VARCHAR | False | False |
| account_role | VARCHAR | False | False |
| profile_mode | VARCHAR | False | False |
| scopes_json | VARCHAR | False | False |
| display_name | VARCHAR | False | False |
| issued_at | DATETIME | False | False |
| subject_user_id | VARCHAR | True | False |
| active_household_id | VARCHAR | True | False |

### biomarker_readings

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | INTEGER | False | True |
| user_id | VARCHAR | False | False |
| name | VARCHAR | False | False |
| value | FLOAT | False | False |
| unit | VARCHAR | True | False |
| reference_range | VARCHAR | True | False |
| measured_at | DATETIME | False | False |
| source_doc_id | VARCHAR | True | False |

### meal_records

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | VARCHAR | False | True |
| user_id | VARCHAR | False | False |
| captured_at | DATETIME | False | False |
| source | VARCHAR | False | False |
| enriched_event | JSON | True | False |
| media_url | VARCHAR | True | False |
| embedding_v1 | JSON | True | False |
| analysis_version | VARCHAR | False | False |
| multi_item_count | INTEGER | False | False |

### medication_regimens

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | VARCHAR | False | True |
| user_id | VARCHAR | False | False |
| medication_name | VARCHAR | False | False |
| canonical_name | VARCHAR | True | False |
| dosage_text | VARCHAR | False | False |
| timing_type | VARCHAR | False | False |
| frequency_type | VARCHAR | False | False |
| frequency_times_per_day | INTEGER | False | False |
| time_rules | JSON | True | False |
| slot_scope | JSON | True | False |
| offset_minutes | INTEGER | False | False |
| fixed_time | VARCHAR | True | False |
| max_daily_doses | INTEGER | False | False |
| instructions_text | VARCHAR | True | False |
| source_type | VARCHAR | False | False |
| source_filename | VARCHAR | True | False |
| source_hash | VARCHAR | True | False |
| start_date | DATE | True | False |
| end_date | DATE | True | False |
| timezone | VARCHAR | False | False |
| parse_confidence | FLOAT | True | False |
| active | BOOLEAN | False | False |

### symptom_checkins

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | VARCHAR | False | True |
| user_id | VARCHAR | False | False |
| recorded_at | DATETIME | False | False |
| severity | INTEGER | False | False |
| free_text | VARCHAR | True | False |
| context | JSON | True | False |
| safety | JSON | True | False |

### user_conditions

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | INTEGER | False | True |
| user_id | VARCHAR | False | False |
| condition_name | VARCHAR | False | False |
| diagnosis_date | DATE | True | False |
| severity | VARCHAR | True | False |
| notes | VARCHAR | True | False |
| is_active | BOOLEAN | False | False |

### user_disliked_ingredients

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | INTEGER | False | True |
| user_id | VARCHAR | False | False |
| ingredient_name | VARCHAR | False | False |

### user_meal_schedules

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | INTEGER | False | True |
| user_id | VARCHAR | False | False |
| day_of_week | INTEGER | False | False |
| meal_type | VARCHAR | False | False |
| time | VARCHAR | False | False |
| notes | VARCHAR | True | False |

### user_nutrition_goals

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | INTEGER | False | True |
| user_id | VARCHAR | False | False |
| goal_type | VARCHAR | False | False |
| target_value | FLOAT | False | False |
| unit | VARCHAR | False | False |
| start_date | DATE | False | False |
| end_date | DATE | True | False |

### meal_components

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | INTEGER | False | True |
| meal_record_id | VARCHAR | False | False |
| component_name | VARCHAR | False | False |
| original_serving_description | VARCHAR | True | False |
| calories_kcal | FLOAT | False | False |
| protein_g | FLOAT | False | False |
| carbohydrates_g | FLOAT | False | False |
| fat_g | FLOAT | False | False |
| sugar_g | FLOAT | False | False |
| sodium_mg | FLOAT | False | False |
| fiber_g | FLOAT | False | False |

### reminder_definitions

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | VARCHAR | False | True |
| user_id | VARCHAR | False | False |
| regimen_id | VARCHAR | True | False |
| reminder_type | VARCHAR | False | False |
| source | VARCHAR | False | False |
| title | VARCHAR | False | False |
| body | VARCHAR | True | False |
| medication_name | VARCHAR | False | False |
| dosage_text | VARCHAR | False | False |
| route | VARCHAR | True | False |
| instructions_text | VARCHAR | True | False |
| special_notes | VARCHAR | True | False |
| treatment_duration | VARCHAR | True | False |
| timezone | VARCHAR | False | False |
| active | BOOLEAN | False | False |

### symptom_codes

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | INTEGER | False | True |
| symptom_checkin_id | VARCHAR | False | False |
| code | VARCHAR | False | False |

### user_medications

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | INTEGER | False | True |
| user_id | VARCHAR | False | False |
| regimen_id | VARCHAR | True | False |
| medication_name | VARCHAR | False | False |
| dosage_text | VARCHAR | False | False |
| frequency_type | VARCHAR | False | False |
| start_date | DATE | True | False |
| end_date | DATE | True | False |
| is_active | BOOLEAN | False | False |
| user_notes | VARCHAR | True | False |

### reminder_definition_channels

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| id | INTEGER | False | True |
| reminder_definition_id | VARCHAR | False | False |
| channel | VARCHAR | False | False |

### reminder_occurrences

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | VARCHAR | False | True |
| reminder_definition_id | VARCHAR | False | False |
| user_id | VARCHAR | False | False |
| scheduled_for | DATETIME | False | False |
| trigger_at | DATETIME | False | False |
| status | VARCHAR | False | False |
| action | VARCHAR | True | False |
| action_outcome | VARCHAR | True | False |
| acted_at | DATETIME | True | False |
| grace_window_minutes | INTEGER | False | False |
| retry_count | INTEGER | False | False |
| last_delivery_status | VARCHAR | True | False |
| metadata_json | JSON | True | False |

### reminder_schedule_rules

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| id | INTEGER | False | True |
| reminder_definition_id | VARCHAR | False | False |
| frequency_type | VARCHAR | False | False |
| frequency_days | JSON | True | False |
| specific_time | TIME | True | False |
| interval_days | INTEGER | True | False |
| start_date | DATE | True | False |
| end_date | DATE | True | False |
| rule_params | JSON | True | False |

### medication_adherence_events

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | VARCHAR | False | True |
| user_id | VARCHAR | False | False |
| regimen_id | VARCHAR | False | False |
| occurrence_id | VARCHAR | False | False |
| status | VARCHAR | False | False |
| scheduled_at | DATETIME | False | False |
| taken_at | DATETIME | True | False |
| source | VARCHAR | False | False |
| metadata_json | JSON | True | False |

### reminder_events

| Column | Type | Nullable | Primary Key |
| --- | --- | --- | --- |
| created_at | DATETIME | False | False |
| updated_at | DATETIME | False | False |
| id | VARCHAR | False | True |
| user_id | VARCHAR | False | False |
| reminder_definition_id | VARCHAR | True | False |
| occurrence_id | VARCHAR | True | False |
| regimen_id | VARCHAR | True | False |
| reminder_type | VARCHAR | False | False |
| title | VARCHAR | False | False |
| body | VARCHAR | True | False |
| medication_name | VARCHAR | False | False |
| scheduled_at | DATETIME | False | False |
| sent_at | DATETIME | True | False |
| delivered_at | DATETIME | True | False |
| acknowledged_at | DATETIME | True | False |
