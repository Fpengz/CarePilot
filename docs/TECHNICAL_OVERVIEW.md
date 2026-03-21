# CarePilot Technical Overview

## Introduction
CarePilot is a next-generation AI Health Companion designed for the **Singapore Innovation Challenge**. It leverages a multi-agent orchestration architecture to provide proactive, longitudinal care for patients managing chronic conditions (Hypertension, Diabetes, Lipids).

## Key Features
- **Hawker Vision (Meal Perception)**: Specialist agent trained to identify Singaporean cuisine and estimate nutritional load from photos or text.
- **Structured Medication Adherence**: Automated prescription parsing and personalized, culturally empathetic nudge strategies.
- **Longitudinal Trend Analysis**: Reasoning agents that correlate meal patterns, biomarker changes (HbA1c, BP), and medication adherence.
- **Clinician-in-the-Loop**: Generates structured digests and risk escalations for professional review.

## Architecture
CarePilot is built as a **feature-first modular monolith**, prioritizing clean boundaries and high observability.

### Multi-Agent Orchestration (LangGraph)
The system has evolved from simple chained prompts to a **Supervisor-led LangGraph** architecture:
1. **Supervisor**: Acts as the central brain, interpreting user intent and clinical context.
2. **Specialists**: Perception nodes (Meal, Meds) and Reasoning nodes (Trend, Adherence, Care Plan) process specific domains.
3. **Blackboard State**: A shared `PatientCaseSnapshot` acts as the single source of truth for all agents during a conversation turn.

### Infrastructure
- **Backend**: FastAPI with pydantic-ai and LangGraph for orchestration.
- **Offloaded Inference**: Heavy ML models (Whisper, BERT) are hosted in a standalone microservice to ensure main API low-latency.
- **Frontend**: Next.js 14 with TanStack Query for robust, high-performance state management.
- **Observability**: Full workflow tracing via `EventTimelineService` and Langfuse.

## Tech Stack
- **Languages**: Python (Backend), TypeScript (Frontend).
- **AI Frameworks**: LangGraph, pydantic-ai, transformers.
- **Data**: SQLite (Durable), Redis (Cache/Distributed Locks), ChromaDB (Vector Search).
- **Deployment**: Docker-ready, microservice-offloaded architecture.
