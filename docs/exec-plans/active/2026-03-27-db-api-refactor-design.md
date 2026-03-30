# Design Document: Comprehensive Database & API Optimization (CarePilot)

> **Superseded:** Execution is now tracked in `docs/exec-plans/in-progress/2026-03-30-today-execution-plan.md`. This design remains as background context.

## 1. Introduction

This document outlines the design for a comprehensive refactor of the CarePilot system's database schema and API data pipelines. The goal is to address technical debt, improve data integrity, enhance performance, and ensure scalability by adopting a schema-first relational redesign and optimizing API interactions. This refactor focuses on normalizing JSON fields, clarifying data relationships, and refining data transfer mechanisms.

## 2. Goals

*   **Robustness & Scalability**: Create a database schema and API architecture that can scale efficiently and handle increasing data volumes and complexity.
*   **Performance Optimization**: Reduce API response times and data pipeline latency by minimizing data transfer, optimizing database queries, and streamlining serialization.
*   **Data Integrity**: Enhance data consistency by normalizing JSON fields into relational tables and enforcing explicit foreign key constraints.
*   **Maintainability**: Simplify the codebase by removing legacy ORM definitions and establishing clear, typed data contracts.
*   **Address Technical Debt**: Resolve issues related to current JSON field usage, potential data redundancies, and inefficient data handling.

## 3. Core Architectural Principles

*   **Relational Purity**: Maximize normalized relational structures for data requiring strong integrity, complex querying, or frequent updates.
*   **Data Contract Clarity**: Define explicit, typed data contracts (Pydantic schemas) for all API interactions.
*   **Performance Focus**: Minimize data transfer, optimize database queries, and streamline data pipelines.
*   **SQLModel & Alembic**: All ORM definitions will use `SQLModel`, and schema changes will be managed exclusively via Alembic migrations.

## 4. Database Schema Redesign

### 4.1. `UserProfileRecord` Normalization

*   **Current State**: `UserProfileRecord` contains numerous JSON fields (`conditions`, `medications`, `nutrition_goals`, `meal_schedule`, etc.).
*   **Proposed Solution**:
    *   **Static Fields in `UserProfileRecord`**: Retain core demographics (name, age, locale, profile_mode, budget_tier).
    *   **New Relational Tables**: Create dedicated tables for dynamic/query-heavy data:
        *   `user_conditions` (user_id, condition_name, diagnosis_date, severity, notes)
        *   `user_medications` (user_id, medication_name, dosage_text, frequency_type, start_date, end_date, linked_regimen_id)
        *   `user_nutrition_goals` (user_id, goal_type, target_value, unit, start_date, end_date)
        *   `user_preferred_cuisines` (user_id, cuisine_name)
        *   `user_macro_focus` (user_id, focus_type, target_value, unit)
        *   `user_meal_schedule_items` (user_id, day_of_week, meal_type, time, notes)
    *   `UserProfileRecord` will link to these new tables via foreign keys.

### 4.2. Medication & Reminder Data Flow Refinement

*   **Current State**: Potential redundancy and unclear relationships between `medication_regimens`, `reminder_definitions`, `reminder_occurrences`, `reminder_events`, and `medication_adherence_events`.
*   **Proposed Solution**:
    *   **Source of Truth**:
        *   `medication_regimens`: Canonical definition of prescribed medication.
        *   `reminder_definitions`: Reminder template, links to `medication_regimens` and `user_profiles`.
        *   `reminder_occurrences`: Tracks specific reminder instances (scheduled, status). Links to `reminder_definitions` and `user_profiles`.
        *   `medication_adherence_events`: Definitive log of actual adherence, linking to `user_profiles`, `medication_regimens`, and `reminder_occurrences`.
        *   `reminder_events`: Assess redundancy; deprecate if covered by other tables or clarify/refine schema if essential.
    *   **Foreign Keys**: Ensure all relationships are enforced.

### 4.3. `WorkflowTimelineEventRecord` Granularity

*   **Current State**: Generic audit log potentially containing structured data that could be better queried in dedicated tables.
*   **Proposed Solution**:
    *   **Assess High-Frequency Data**: Identify structured data in `WorkflowTimelineEventRecord.payload` and other tables (e.g., meal analysis, symptom data).
    *   **Specialized Tables**: Create tables for frequently queried, structured data (e.g., `meal_analysis_results`).
    *   `WorkflowTimelineEventRecord` will log event occurrence and reference specialized tables, maintaining audit trail while enabling efficient detailed data queries.

### 4.4. `MealRecordRecord` & `BiomarkerReadingRecord` Refinement

*   **Current State**: JSON fields (`meal_state`, `meal_perception`, `enriched_event`, `embedding_v1`, etc.) may benefit from more structured handling.
*   **Proposed Solution**:
    *   **Meal Records**: Normalize `meal_state` and `meal_perception` if specific components are frequently accessed/filtered. `embedding_v1` remains JSON/Array for vector search.
    *   **Biomarker Readings**: Standardize columns. Consider ENUMs or lookup tables for `name` and `unit` if values are limited, for consistency and performance.

### 4.5. Elimination of Legacy ORM Definitions

*   **Action**: Scan codebase for non-`SQLModel` ORM definitions and migrate them to `SQLModel`.

### 5. API Data Pipeline Optimization

#### 5.1. Reducing API Context Size & Payload Overload

*   **Proposed Solution**:
    *   **API Endpoint Design**:
        *   **Selective Field Retrieval**: Use query parameters or Pydantic `model_fields_set` for clients to request specific fields.
        *   **DTOs**: Employ Pydantic models as lean Data Transfer Objects for API requests/responses.
        *   **Pagination**: Implement pagination for all list endpoints.
    *   **`PatientCaseSnapshot` Handling**:
        *   **Granular Loading**: Assemble snapshot components on-demand.
        *   **Caching**: Implement caching for static/frequently accessed parts.
        *   **Background Projections**: Offload complex snapshot generation to background workers.
    *   **JSON Optimization**: Index JSON fields in database queries where applicable.

#### 5.2. Frontend-Backend Data Flow Enhancement

*   **Proposed Solution**:
    *   **Leaner API Responses**: Ensure API returns only necessary data.
    *   **TanStack Query**: Leverage frontend caching and data deduplication.
    *   **Eventual Consistency**: Use for non-critical updates to improve API responsiveness.

### 6. Validation and Migration Strategy

*   **Alembic Migrations**: All schema changes managed via Alembic scripts.
*   **Testing**: Unit, Integration, and E2E tests will be updated/created. Performance benchmarking will be conducted.
*   **Observability**: Ensure `WorkflowTimelineEventRecord` is updated, and new structures are logged if necessary.

---
*Date: 2026-03-27*
*Author: Gemini CLI Agent*
*Topic: Database & API Refactor Design*
---
*The content above has been saved to docs/exec-plans/active/2026-03-27-db-api-refactor-design.md*
