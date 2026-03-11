# Dietary Tools - Codebase Documentation Index

> **Status**: Archived snapshot (pre feature-first refactor).  
> **Last Reviewed**: March 12, 2026  
> **Scope (historical)**: services/*, agents/*, llm/*, application/*  
> **Current reference**: `ARCHITECTURE.md` and `docs/developer-guide.md`

---

## 📑 Documentation Files

### 1. **CODEBASE_MAP.md** (28 KB | 620 lines)
   **Purpose**: Comprehensive reference guide with detailed descriptions of every module
   
   **Contents**:
   - **Part 1**: Services Layer - 39 files organized by responsibility
     - Nutrition & Meal Analysis (4 files)
     - Health Profile & Personalization (3 files)
     - Recommendation & Clinical Logic (3 files)
     - Notification & Reminder Management (5 files)
     - Alerting & Outbox (2 files)
     - Media & File Handling (2 files)
     - Policy & Access Control (2 files)
     - Tool & Workflow Management (3 files)
     - Memory & State (1 file)
     - Utilities & Infrastructure (4 files)
     - Advanced Services (6 files)
     - Channels Subpackage (4 files)
   
   - **Part 2**: Agents Layer - 5 files
     - dietary.py, vision.py, executor.py, registry.py
   
   - **Part 3**: LLM Layer - 4 files
     - factory.py, routing.py, types.py, __init__.py
   
   - **Part 4**: Application Layer - 14 packages
     - 14 domain-driven use case modules
   
   - **Part 5**: Dependency Analysis
     - Import flow diagrams
     - Cross-module dependencies
     - Apps/API dependencies
   
   - **Part 6**: Analysis
     - Overlapping responsibilities (4 identified)
     - Re-export chains
     - Dead code candidates
     - Consolidation opportunities
     - Service complexity breakdown
     - Well-designed patterns
   
   - **Part 7**: Recommendations
     - Architecture improvements
     - Strengths & weaknesses

---

### 2. **CODEBASE_SUMMARY.txt** (9.1 KB | 149 lines)
   **Purpose**: Quick reference with key findings and action items
   
   **Contents**:
   - File inventory (services, agents, llm, application)
   - Dependency map (apps → application → services/agents/llm)
   - ⚠️ Key Findings (5 major concerns):
     1. Two recommendation services (naming conflict)
     2. Logic scattered across layers
     3. Large monolithic service (675 lines)
     4. Potentially dead code
     5. Poor service layer boundaries
   - ✅ Well-designed patterns (5 examples)
   - 🎯 Recommended actions (6 items with priority)

   **Best for**: Quick overview, presenting to team, identifying quick wins

---

### 3. **DEPENDENCY_GRAPH.txt** (17 KB | 350+ lines)
   **Purpose**: Detailed dependency chains showing imports and dependents
   
   **Contents**:
   - 🍽️ Food & Nutrition Chain
   - 💊 Recommendation & Clinical Chain
   - ⏰ Alert & Reminder Chain (core infrastructure)
   - 🏥 Health Profile Chain
   - 🛠️ Policy & Tool Management Chain
   - 🔄 Workflow & Memory Chain
   - 📊 Metrics & Analytics
   - 🎬 Media & Capture
   - 📡 Transports & Channels
   - 🧰 Utilities
   - 🤖 Inference Layer (agents)
   - 🧠 LLM Abstraction (llm)
   - 🎯 Master Orchestrator (application)
   - 📋 Domain Use Cases (application)
   - Summary of critical paths

   **Best for**: Tracing dependencies, understanding data flow, refactoring decisions

---

## 🔍 Quick Reference Tables

### Services by Category

| Category | Files | Purpose | Lines |
|----------|-------|---------|-------|
| **Nutrition** | 4 | Meal catalog, food ranking, nutrition summaries | ~650 |
| **Health** | 3 | Profiles, onboarding, completeness | ~400 |
| **Recommendations** | 3 | Simple + advanced + clinical parsing | ~850 |
| **Notifications** | 5 | Reminders, medications, mobility alerts | ~650 |
| **Alerting** | 2 | Alert pub/sub + outbox pattern | ~580 |
| **Media** | 2 | Image upload, duplicate detection | ~310 |
| **Policy** | 4 | Authorization, policies, tool registry | ~340 |
| **Workflow** | 2 | Orchestration, in-memory caches | ~180 |
| **Utilities** | 4 | Timezone, messaging, dependencies | ~95 |
| **Channels** | 4 | Telegram, WhatsApp, WeChat transports | ~200 |
| **Advanced** | 6 | Dashboard, social, metrics, emotion, etc. | ~450 |

### Most Critical Modules (by usage frequency)

| Module | Usage Count | Reason |
|--------|-------------|--------|
| `health_profile_service.py` | 7+ | Core user data |
| `meal_record_utils.py` | 8+ | Utility extractors |
| `canonical_food_service.py` | 4+ | Food database |
| `alerting_service.py` | 4+ | Core infrastructure |
| `reminder_scheduler.py` | 2+ | Background jobs |

### Largest Services (by line count)

| Module | Lines | Candidate for Refactor? |
|--------|-------|------------------------|
| `recommendation_agent_service.py` | 675 | ⚠️ Yes - split into 3 modules |
| `alerting_service.py` | 538 | ✅ Well-designed (outbox pattern) |
| `canonical_food_service.py` | 397 | ✅ OK - complex algorithm |
| `notification_service.py` | 350 | ✅ OK - multi-channel logic |
| `daily_suggestions_service.py` | 260 | ⚠️ Move to application layer |

---

## ⚠️ Key Issues Identified

### 1. **Two Recommendation Services** (Naming Conflict)
- `recommendation_service.py` (102 lines) - Simple, stateless
- `recommendation_agent_service.py` (675 lines) - Complex, stateful
- **Action**: Rename for clarity

### 2. **Logic Scattered Across Layers**
- Meal normalization: agents/vision.py vs application/meals/use_cases.py
- Daily suggestions: services/daily_suggestions_service.py vs application/suggestions/use_cases.py
- **Action**: Consolidate to application layer

### 3. **Monolithic Service**
- `recommendation_agent_service.py` (675 lines)
- **Action**: Split into 3 smaller modules (max 300 lines each)

### 4. **Dead Code Candidates**
- `dashboard_service.py` - No imports found
- `social_service.py` - No imports found
- `profile_tools_service.py` - No imports found
- **Action**: Audit and remove or document

### 5. **Poor Service Layer Boundaries**
- Services mix infrastructure, utilities, and orchestration
- **Action**: Define clear service layer contract

---

## ✅ Well-Designed Patterns

1. **LLMFactory** - Clean abstraction over multiple LLM providers (OpenAI, Gemini, Ollama, vLLM)
2. **Repository Pattern** - Protocol-based interfaces (ports.py)
3. **Outbox Pattern** - Reliable async message delivery (alerting_service)
4. **Channel Abstraction** - Pluggable notification transports
5. **Tool Registry** - Extensible tool registration and execution

---

## 🎯 Recommended Actions (Priority Order)

### Immediate (High Impact)
1. **Rename services** for clarity:
   - `recommendation_service` → `simple_recommendation_service`
   - `recommendation_agent_service` → `advanced_recommendation_agent_service`

2. **Move daily_suggestions_service** to application layer
   - Remove 260 lines from services
   - Reduces architectural confusion

3. **Consolidate meal normalization**
   - Move logic from agents/vision.py to application/meals/use_cases.py
   - Agent stays perception-only

### Medium (Cleanup)
4. **Audit dead code**
   - dashboard_service.py
   - social_service.py
   - profile_tools_service.py

5. **Refactor recommendation_agent_service**
   - Split into 3 modules: preference_tracking, substitution_scoring, interaction
   - Max 300 lines per module

### Long-Term (Architecture)
6. **Document service layer contract**
   - Services = Stateless utilities only
   - Orchestration = Application layer only
   - Infrastructure = Infrastructure layer only

---

## 📊 Architecture Overview

```
┌──────────────────────────────────┐
│       External Apps              │
│  (api, workers, tests)           │
└───────────────┬──────────────────┘
                │
                ▼
        ┌──────────────────┐
        │  Application     │  (Use cases, orchestration)
        │  Layer (14 pkg)  │
        └────────┬─────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌────────────────────────────────────────┐
│  Services (39) │ Agents (5) │ LLM (4) │
│  Utilities,    │ Inference  │ Factory │
│  Infrastructure│ Engines    │ Routing │
└────────────────┼────────────────────┬─┘
                 │                    │
                 └────────┬───────────┘
                          ▼
                 ┌──────────────────┐
                 │ Domain & Models  │
                 │ Infrastructure   │
                 └──────────────────┘
```

---

## 🔗 Import Chains Summary

**Heaviest Dependency Chains**:
1. `health_profile_service` ← 7+ consumers
2. `meal_record_utils` ← 8+ consumers
3. `canonical_food_service` ← 4+ consumers (agents, apps, services)
4. `alerting_service` ← 4+ consumers (core infrastructure)

**Key Data Flows**:
- **Meal Processing**: capture → vision.py → application/meals → services.canonical_food
- **Recommendations**: health_profile + meal_record → recommendation services → application
- **Alerts**: services.alerting → notification → channels → transport
- **Workflows**: coordinator → memory + tool_registry → outcomes

---

## 📚 How to Use This Documentation

### For New Team Members
1. Start with **CODEBASE_SUMMARY.txt** for quick overview
2. Read **CODEBASE_MAP.md** Part 1-4 for module descriptions
3. Use **DEPENDENCY_GRAPH.txt** to understand data flow

### For Refactoring Decisions
1. Check **CODEBASE_MAP.md** Part 6 (Overlaps & Opportunities)
2. Review **DEPENDENCY_GRAPH.txt** to understand impact
3. Reference **CODEBASE_SUMMARY.txt** for recommended actions

### For Adding New Features
1. Identify use case area in application layer
2. Check which services it depends on
3. Use **DEPENDENCY_GRAPH.txt** to understand existing patterns
4. Follow well-designed patterns from Part 6 of CODEBASE_MAP.md

### For Performance Analysis
1. Review "Largest Services" table above
2. Check **DEPENDENCY_GRAPH.txt** for circular dependencies
3. Reference "Critical Paths" section

---

## 🏗️ Architecture Decisions Made

### Strengths ✅
- Clear 3-tier architecture (services → application → API)
- Good LLM provider abstraction
- Protocol-based interfaces (repository pattern)
- Async/concurrent support
- Multi-channel notification system

### Weaknesses ❌
- Services layer has mixed responsibilities
- Logic split across services and application (meal normalization, suggestions)
- Large monolithic services (recommendation_agent: 675 lines)
- Unused services not cleaned up
- Daily suggestions duplicated

### Current Pattern
- **Services**: Utilities + Infrastructure (NOT stateless as named)
- **Application**: Use cases + orchestration
- **Agents**: LLM inference wrappers
- **LLM**: Provider abstraction factory

---

## 📝 Changelog

| Date | Change |
|------|--------|
| 2024-03-10 | Initial comprehensive documentation |

---

## 💡 Notes

- All statistics current as of the codebase snapshot analyzed
- Line counts approximate (headers/docstrings included)
- "Dead code" candidates need verification before removal
- Refactoring recommendations assume no breaking API changes needed
