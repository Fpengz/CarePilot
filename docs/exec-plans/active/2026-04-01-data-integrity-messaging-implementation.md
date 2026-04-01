# Data Integrity & Messaging: Projections and Webhook Normalization Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden data integrity and messaging pipelines by verifying projections replay and normalizing inbound message webhooks.

**Architecture:** 
1.  Verify the `projections replay` CLI command ensures event timeline rebuilds correctly.
2.  Implement a standard normalization layer for inbound webhooks (e.g., Telegram, SMS) to ensure a uniform `InboundMessage` shape.
3.  Stabilize attachment handling across messaging channels.

**Tech Stack:** Python, SQLModel, LangGraph.

---

## Chunk 1: Projections Replay Verification

### Task 1: Verify Projections Replay

**Files:**
- Modify: `scripts/cli/commands/projections.py` (if needed)
- Test: `tests/integration/test_projections_replay.py`

- [ ] **Step 1: Audit existing `projections.py` replay logic**

- [ ] **Step 2: Create an integration test that seeds events and triggers replay**
  Verify that the resulting projections (e.g., Clinical Snapshot) match expected states.

- [ ] **Step 3: Fix any discrepancies in replay logic**

- [ ] **Step 4: Commit**

---

## Chunk 2: Webhook Normalization

### Task 2: Standardize Inbound Messages

**Files:**
- Modify: `apps/api/carepilot_api/routers/webhooks.py`
- Create: `src/care_pilot/features/companion/messaging/normalization.py`

- [ ] **Step 1: Define `InboundMessage` canonical schema**

- [ ] **Step 2: Implement normalization for Telegram webhooks**

- [ ] **Step 3: Implement normalization for SMS webhooks**

- [ ] **Step 4: Update webhook router to use the normalization layer**

- [ ] **Step 5: Commit**

---

## Chunk 3: Attachment Handling

### Task 3: Stabilize Multi-channel Attachments

**Files:**
- Modify: `src/care_pilot/features/companion/chat/orchestrator.py`

- [ ] **Step 1: Ensure image/audio attachments are consistently passed to the LangGraph workflow**

- [ ] **Step 2: Verify with a test case involving an image upload**

- [ ] **Step 3: Commit**

---

## Chunk 4: Final Verification

### Task 4: Messaging & Integrity Gate

- [ ] **Step 1: Run messaging tests**

- [ ] **Step 2: Run comprehensive gate**

- [ ] **Step 3: Commit and Open PR**
