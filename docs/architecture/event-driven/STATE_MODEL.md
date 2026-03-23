# State Model (PatientCaseSnapshot)

## Overview

CarePilot uses a centralized state model:

PatientCaseSnapshot

This acts as the system's shared blackboard for companion workflows and is
materialized by deterministic projectors.

## Responsibilities

- Unify patient data for personalization
- Provide context to agents
- Ensure consistency across features

## Snapshot Sections (Owned Projections)

To reduce write conflicts and improve replay safety, the snapshot is split into
owned sections. Each section is updated by one or more designated projectors.

Example sections:

- Demographics & preferences summary
- Medications & adherence summary
- Meal & nutrition summary
- Trends & vitals summary
- Conversation summary

Each section includes metadata:

- `schema_version`
- `projection_version`
- `source_event_cursor`

## Components

### 1. Static State

- Demographics
- Conditions
- Medications

### 2. Dynamic State

- Recent meals
- Symptoms
- Adherence events

### 3. Derived State

- Trends
- Risk flags
- Engagement level

## Access Pattern

Agents are read-only. Features own reads and writes. Services execute the writes.

## Source of Truth

State is derived from:

- Database records
- Timeline events
- Feature computations

## Key Rule

Agents never mutate state directly.
