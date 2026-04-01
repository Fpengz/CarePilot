# Legacy Retirement: Remove Orchestration-First Assumptions Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the transition to the feature-first LangGraph architecture by retiring legacy orchestration-first patterns.

**Architecture:** 
1.  Identify and remove `RecommendationAgent` (legacy version) if superseded by specialized agents in LangGraph.
2.  Clean up `ChatOrchestrator` to remove synchronous multi-agent branching that is now handled by the Supervisor node in LangGraph.
3.  Update `ARCHITECTURE.md` to establish LangGraph as the canonical orchestration engine.

**Tech Stack:** Python, LangGraph.

---

## Chunk 1: Legacy Agent Retirement

### Task 1: Remove Redundant RecommendationAgent

**Files:**
- Delete: `src/care_pilot/agent/recommendation/agent.py` (if fully redundant)
- Modify: `src/care_pilot/agent/core/registry.py`

- [ ] **Step 1: Verify `RecommendationAgent` usage in codebase**

- [ ] **Step 2: Remove the file and its references if confirmed redundant**

- [ ] **Step 3: Commit**

---

## Chunk 2: Orchestrator Cleanup

### Task 2: Simplify ChatOrchestrator

**Files:**
- Modify: `src/care_pilot/features/companion/chat/orchestrator.py`

- [ ] **Step 1: Remove legacy intent classification logic that bypassed the graph**

- [ ] **Step 2: Ensure all chat entries flow through `stream_multi_agent_workflow`**

- [ ] **Step 3: Commit**

---

## Chunk 3: Documentation Update

### Task 3: Canonical Architecture Update

**Files:**
- Modify: `ARCHITECTURE.md`

- [ ] **Step 1: Update "Orchestration" section to describe Supervisor-led LangGraph**

- [ ] **Step 2: Remove mentions of "orchestration-first" or "central brain" patterns**

- [ ] **Step 3: Commit**

---

## Chunk 4: Final Verification

### Task 4: Clean Slate Gate

- [ ] **Step 1: Run all tests to ensure no broken imports from deleted legacy code**

- [ ] **Step 2: Run comprehensive gate**

- [ ] **Step 3: Commit and Open PR**
