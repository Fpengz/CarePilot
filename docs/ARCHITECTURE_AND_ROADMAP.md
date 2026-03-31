# CarePilot Master Architecture & Roadmap

**Version**: 2.0 (Harness-Aligned)  
**Status**: Active Development  
**Last Updated**: 2024-05-23  
**Owner**: Engineering Team  

---

## 1. Executive Summary

This document defines the target architecture, resilience patterns, and execution roadmap for CarePilot. It consolidates technical debt remediation, performance optimization (<100ms latency), and advanced AI feature pipelines (Meal, Medication, Emotion) into a single source of truth.

**Design Philosophy**: Aligned with [Anthropic's Harness Principles](https://www.anthropic.com/engineering/harness-design-long-running-apps):
1.  **Explicit State**: No hidden side effects; all state transitions are logged and idempotent.
2.  **Resilience First**: Circuit breakers, retries, and graceful degradation are default, not optional.
3.  **Observability**: Metrics, traces, and logs are intrinsic to the code, not add-ons.
4.  **Modular Pipelines**: Complex flows are broken into atomic, testable stages.

---

## 2. Current State Assessment & Technical Debt

### 2.1 Critical Debts (P0 - Immediate Action)
| ID | Issue | Risk | Remediation Strategy |
|----|-------|------|----------------------|
| TD-01 | Hardcoded Configs | High | Centralize in `config/settings.py` with env var overrides. |
| TD-02 | Sync I/O in Async | High | Replace `time.sleep`/blocking DB calls with `asyncio` equivalents. |
| TD-03 | Missing Idempotency | Critical | Implement `Idempotency-Key` header check with Redis locking for all POST/PUT. |
| TD-04 | Debug Prints | Medium | Replace with structured `structlog` logging; remove prints from `main.py`. |

### 2.2 Architectural Gaps (P1 - Phase 1-2)
- **Tight Coupling**: Agents directly instantiate dependencies. -> **Fix**: Dependency Injection via Service Container.
- **No Migration History**: Schema drift risk. -> **Fix**: Enforce Alembic migrations for all DB changes.
- **N+1 Queries**: Latency spikes under load. -> **Fix**: Audit ORM usage, enforce `selectinload`/`joinedload`.

---

## 3. Target Architecture Design

### 3.1 High-Level Topology (Hexagonal)
```mermaid
graph TD
    Client[Web/Mobile Client] --> API_GW[API Gateway / Rate Limiter]
    API_GW --> Orchestrator[Companion Orchestrator]
    
    subgraph "Core Services (Async)"
        Orchestrator --> Agent_Reg[Agent Registry]
        Agent_Reg --> Mem_Layer[Memory & Context Layer]
        Agent_Reg --> Tool_Run[Tool Executor]
    end
    
    subgraph "Async Pipelines (Queue Driven)"
        Orchestrator --> Kafka[Message Bus (Kafka/RabbitMQ)]
        Kafka --> Meal_W[Meal Analysis Worker]
        Kafka --> Med_W[Medication OCR Worker]
        Kafka --> Emo_W[Emotion Analysis Worker]
        Kafka --> Rem_W[Reminder Scheduler]
    end
    
    subgraph "Data Stores"
        Mem_Layer --> Redis[Cache & Short-term Memory]
        Mem_Layer --> Qdrant[Vector DB (Long-term)]
        Mem_Layer --> Postgres[Relational DB (User/Family)]
    end
```

### 3.2 Performance Budget (<100ms P95 for Chat)
| Component | Budget | Strategy |
|-----------|--------|----------|
| **Context Pruning** | 15ms | Sliding window + Semantic cache (Redis). |
| **Memory Retrieval** | 20ms | HNSW Index on Qdrant; Pre-filtered by User ID. |
| **RL Inference** | 10ms | Lightweight Thompson Sampling (Local Model). |
| **LLM Generation** | 45ms | Streaming response; Smaller model for intent, larger for complex reasoning. |
| **Network/Overhead** | 10ms | gRPC internal comms; Connection pooling. |

---

## 4. Core System Enhancements

### 4.1 Context Pruning & Memory Layer
**Goal**: Maintain relevant context without exceeding token limits or latency budgets.

**Implementation**: `src/care_pilot/platform/memory/context_pruner.py`
- **Tier 1 (Permanent)**: System prompts, User Allergies, Critical Health Facts (Always included).
- **Tier 2 (Sliding Window)**: Last 5 conversation turns (Raw text).
- **Tier 3 (Semantic)**: Vector search for historical relevance (Top-K matches).
- **Forgetting Curve**: Apply time-decay scoring to Tier 3 items; prune score < threshold.

### 4.2 Message Channel Robustness
**Protocol**: Internal gRPC with Protocol Buffers (40% smaller payload than JSON).
**Resilience Patterns**:
- **Idempotency**: Every request requires `X-Idempotency-Key`. Redis stores `{key: response_hash}` for 24h.
- **Dead Letter Queue (DLQ)**: Failed messages after 3 retries move to DLQ for manual inspection.
- **Circuit Breaker**: If LLM/DB error rate > 50% in 1min, open circuit -> Return cached fallback response.

### 4.3 Reinforcement Learning (RL) Integration
**Phase 1 (Weeks 1-8)**: Contextual Multi-Armed Bandits (Thompson Sampling).
- **Action Space**: Recommendation styles (Direct, Empathetic, Data-Driven).
- **Reward Signal**: User Acceptance (+1), Engagement Time (+0.2), Explicit Rejection (-1).
- **Deployment**: Run alongside main logic; log decisions for offline evaluation.

**Phase 2 (Weeks 9-16)**: Deep RL (PPO) for complex sequential planning (e.g., multi-day meal planning).

---

## 5. Specialized AI Pipelines

### 5.1 Meal Analysis Pipeline
**Trigger**: User uploads image or describes food.
**Stages**:
1.  **Vision**: CLIP/Food-101 model identifies food items (Confidence > 0.8).
2.  **Estimation**: Estimate portion size via depth cues or user prompt.
3.  **Nutrition**: Query USDA API for macros/micros.
4.  **Verification**: If confidence < 0.8, trigger Clarification Agent ("Did you mean pasta or rice?").
5.  **Log**: Commit to `meal_logs` table; update daily calorie counter.

### 5.2 Medication Parsing + OCR Pipeline
**Trigger**: User uploads photo of prescription bottle.
**Stages**:
1.  **OCR**: EasyOCR/Tesseract extracts text.
2.  **NER**: BioBERT extracts `Drug Name`, `Dosage`, `Frequency`, `Instructions`.
3.  **Safety Check**: Cross-reference with `user_allergies` and `current_medications` (Drug-Drug Interaction check).
4.  **Confirmation**: Present parsed data to user for approval.
5.  **Scheduling**: Create recurring reminders in Reminder System.

### 5.3 Emotion Analysis & Persona Switching
**Trigger**: Every user message.
**Model**: DistilBERT (Sentiment) + Emotion Classification (Joy, Sadness, Anger, Anxiety).
**Actions**:
-   **Crisis Detection**: If `Suicide/Self-Harm` intent detected -> Trigger Escalation Protocol (Human support resources).
-   **Persona Shift**:
    -   *Anxiety Detected* -> Switch to "Calm Counselor" persona (Softer tone, validation).
    -   *Low Motivation* -> Switch to "Supportive Coach" persona (Encouragement, small steps).
-   **Logging**: Store emotion vector in `conversation_metadata` for trend analysis.

### 5.4 Reminder System Refactoring
**Current Issue**: Simple cron jobs; no context awareness.
**New Design**: Distributed Smart Scheduler (Celery Beat + Redis).
**Features**:
-   **Smart Suppression**: Do not notify if `user_sleep_status` == true or `do_not_disturb` active.
-   **Adaptive Rescheduling**: If user dismisses 3x, suggest new time or reduce frequency.
-   **Contextual Nudges**: "You usually walk after lunch. Ready for your 1pm walk?" (Based on historical patterns).

---

## 6. Family & Social Module

### 6.1 Data Model Extensions
-   **Care Circles**: `User` belongs to `FamilyGroup`. Roles: `Admin`, `Caregiver`, `Member`, `Viewer`.
-   **Permissions**: Granular scopes (`view_meals`, `edit_meds`, `receive_alerts`).
-   **Consent**: Explicit digital consent record required for sharing health data.

### 6.2 Feature Opportunities
-   **Shared Goals**: "Family Step Challenge" with aggregated anonymized data.
-   **Caregiver Dashboard**: View adherence trends, receive critical alerts (missed meds).
-   **Emergency Access**: Break-glass protocol for emergency contacts to view critical allergies/conditions.

---

## 7. Evaluation & Observability

### 7.1 Key Metrics (Dashboard)
| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| **Chat Latency (P95)** | < 100ms | > 150ms |
| **Hallucination Rate** | < 1% | > 2% |
| **Intent Accuracy** | > 95% | < 90% |
| **Pipeline Error Rate** | < 0.1% | > 1% |
| **Reminder Acceptance** | > 45% | < 30% |

### 7.2 Tooling Stack
-   **Tracing**: OpenTelemetry -> Grafana Tempo.
-   **Metrics**: Prometheus -> Grafana.
-   **LLM Eval**: RAGAS (Offline), LangSmith (Online Tracing).
-   **Error Tracking**: Sentry (with User Context).

---

## 8. Execution Roadmap (16 Weeks)

### Phase 1: Stability & Foundation (Weeks 1-4)
-   [ ] **Refactor**: Remove sync I/O, centralize config, implement structured logging.
-   [ ] **Resilience**: Add Circuit Breakers and Idempotency Keys to API.
-   [ ] **Context**: Implement `ContextPruner` with sliding window.
-   [ ] **Ops**: Setup Prometheus/Grafana dashboards.

### Phase 2: AI Pipelines MVP (Weeks 5-8)
-   [ ] **Meal**: Integrate Vision model + USDA API.
-   [ ] **Meds**: Build OCR + BioBERT parser pipeline.
-   [ ] **Emotion**: Deploy Sentiment Analysis middleware.
-   [ ] **Family**: Implement Role-Based Access Control (RBAC).

### Phase 3: Optimization & RL (Weeks 9-12)
-   [ ] **Performance**: Optimize DB queries (fix N+1), implement caching layers.
-   [ ] **RL**: Deploy Contextual Bandit for recommendation styling.
-   [ ] **Reminders**: Migrate to Smart Scheduler with suppression logic.
-   [ ] **Testing**: Increase unit test coverage to >80%.

### Phase 4: Production Hardening (Weeks 13-16)
-   [ ] **Security**: Penetration testing, HIPAA compliance audit.
-   [ ] **Scale**: Load testing (target 10k concurrent users).
-   [ ] **Rollout**: Canary deployment of new architecture.
-   [ ] **Feedback**: Launch User Feedback Loop for continuous improvement.

---

## 9. Immediate Next Steps
1.  **Sprint Planning**: Break down Phase 1 tasks into Jira tickets.
2.  **Code Audit**: Run static analysis (SonarQube) to identify remaining sync blocks.
3.  **Schema Design**: Draft SQL migrations for Family/Role tables.
4.  **Tool Selection**: Finalize Vector DB (Qdrant vs Pinecone) and OCR provider.
