# Today's Implementation Plan - 2026-03-27

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the core structural and agentic layers of CarePilot to ensure production-grade reliability, data integrity, and multi-modal messaging support.

**Architecture:** 
1.  **Structural**: Migrate from schema-less JSON fields to normalized relational tables using SQLModel/Alembic.
2.  **Agentic**: Consolidate and unify chat and emotion inference into a robust, high-performance async runtime.
3.  **Connectivity**: Generalize message contracts to support full-duplex inbound/outbound flows with rich multi-modal attachments.

**Tech Stack:** Python (FastAPI, SQLModel, Alembic, LangGraph), TypeScript (Next.js, Tailwind, TanStack Query, Playwright).

---

## Chunk 1: Database Normalization (Structural Hardening)

### Task 1: Implement Normalized Models
**Files:**
- Modify: `src/care_pilot/platform/persistence/models/profiles.py` (Add relationships)
- Create: `src/care_pilot/platform/persistence/models/user_nutrition_goals.py`
- Create: `src/care_pilot/platform/persistence/models/user_meal_schedule.py`
- Modify: `src/care_pilot/platform/persistence/models/__init__.py`

- [ ] **Step 1: Define UserNutritionGoalRecord and UserMealScheduleRecord**
- [ ] **Step 2: Generate Alembic migration**
- [ ] **Step 3: Run migration and verify tables**

### Task 2: Update Profile Service to use Relational Tables
**Files:**
- Modify: `src/care_pilot/features/profiles/profile_service.py`
- Test: `tests/features/test_profile_persistence.py`

- [ ] **Step 1: Write test for persisting and retrieving profile with normalized tables**
- [ ] **Step 2: Update ProfileService.save_profile to write to new tables**
- [ ] **Step 3: Update ProfileService.get_profile to read from new tables**
- [ ] **Step 4: Verify tests pass**

---

## Chunk 2: Agent & Chat Consolidation

### Task 3: Clean up ChatOrchestrator Legacy Code
**Files:**
- Modify: `src/care_pilot/features/companion/chat/orchestrator.py`

- [ ] **Step 1: Identify and remove methods: `_merge_agent_response`, `_apply_safety_policy`, `_merge_agent_actions`**
- [ ] **Step 2: Ensure all inference logic correctly routes through the supervisor-led graph**
- [ ] **Step 3: Verify chat functionality in dev mode**

### Task 4: Centralize EmotionAgent Runtime
**Files:**
- Modify: `src/care_pilot/agent/emotion/agent.py`
- Modify: `src/care_pilot/platform/app_context.py`

- [ ] **Step 1: Ensure EmotionAgent is the single entry point for all emotion inference**
- [ ] **Step 2: Add shared async background tasks for emotion processing if needed for performance**
- [ ] **Step 3: Update AppContext to provide a unified EmotionAgent instance**

---

## Chunk 3: Messaging & Multi-Modal Integration

### Task 5: Support Full-Duplex Inbound Messaging
**Files:**
- Create: `apps/api/carepilot_api/routers/webhooks.py`
- Modify: `src/care_pilot/features/reminders/reminder_service.py` (Add inbound handlers)

- [ ] **Step 1: Implement Telegram webhook endpoint**
- [ ] **Step 2: Map inbound messages to ChatOrchestrator or ReminderService actions**
- [ ] **Step 3: Implement basic inbound message logging**

### Task 6: Rich Attachment Support
**Files:**
- Modify: `src/care_pilot/features/reminders/domain/models.py` (Verify MessageAttachment)
- Modify: `src/care_pilot/platform/messaging/alert_outbox.py` (Add attachment handling)

- [ ] **Step 1: Ensure outbound workers can process MessageAttachment objects**
- [ ] **Step 2: Update Telegram/WhatsApp sinks to support sending images/audio**

---

## Chunk 4: Quality Assurance

### Task 7: E2E Validation
**Files:**
- Create: `apps/web/e2e/full-journey.spec.ts`

- [ ] **Step 1: Implement full journey test (Login -> Profile Setup -> Med Intake -> Meal Log -> Chat)**
- [ ] **Step 2: Run `pnpm web:e2e` and ensure 100% pass rate**

---

## Technical Debt Observations & Architecture Design for Robustness

### Low Latency
- **Background Projection**: Already implemented for snapshots, but should be extended to complex dashboard calculations.
- **Cache-Aside Pattern**: Implement for LLM-heavy features like Clinical Cards and Summaries.

### High Accuracy
- **RAG Refinement**: Improve chunking and retrieval relevance for medical knowledge.
- **Human-in-the-loop**: Enhance the "Review" phase for medication and meal normalization.

### Robustness
- **Transactional Consistency**: Use the Outbox pattern for ALL side effects (e.g., timeline events, telemetry).
- **Graceful Degradation**: Ensure the UI remains functional even if emotion inference or specialized agents are slow/down.
