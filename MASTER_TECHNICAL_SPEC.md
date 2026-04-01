# CarePilot Master Technical Specification & Roadmap

## Executive Summary
This document consolidates findings on technical debt, architectural improvements, and new feature pipelines. It serves as the blueprint for transforming CarePilot into a sub-100ms latency, production-grade health platform with advanced AI capabilities.

---

## 1. Architectural Redesign: Hexagonal & Event-Driven

### Current Issues
- Tight coupling between `CompanionOrchestrator` and specific agent classes.
- Synchronous blocking calls in async paths.
- Lack of clear boundaries between domain logic and infrastructure.

### Target Architecture
We will shift to a **Hexagonal Architecture** supported by an **Event-Driven Backbone**.

#### Core Principles
1.  **Ports & Adapters:** Agents define `interfaces` (ports); LLM providers, DBs, and External APIs are `adapters`.
2.  **Async-First:** All I/O operations must be non-blocking. Heavy tasks offloaded to workers.
3.  **Dependency Injection:** Explicit injection of dependencies for testability.

#### Proposed Module Structure
```text
src/care_pilot/
├── core/                   # Domain Logic (Entities, Value Objects)
│   ├── entities/           # User, Conversation, Medication, Meal
│   ├── value_objects/      # HealthMetrics, EmotionScore
│   └── interfaces/         # Ports (Repository, LLMProvider, Scheduler)
├── application/            # Use Cases & Orchestration
│   ├── services/           # CompanionService, MedicationParser
│   ├── dtos/               # Data Transfer Objects
│   └── commands/           # CQRS Commands
├── infrastructure/         # Adapters
│   ├── db/                 # SQLAlchemy/AsyncPG implementations
│   ├── llm/                # OpenAI/Anthropic adapters
│   ├── ocr/                # Tesseract/EasyOCR wrappers
│   └── messaging/          # Redis/RabbitMQ producers/consumers
├── api/                    # Entry Points
│   ├── rest/               # FastAPI routers
│   └── grpc/               # Internal high-performance RPC
└── workers/                # Background Tasks
    ├── meal_analysis.py
    ├── ocr_pipeline.py
    └── reminder_dispatcher.py
```

---

## 2. Message Channel Optimization

### Performance & Robustness Strategy
To achieve <100ms end-to-end latency and ensure reliability:

| Component | Technology | Benefit |
| :--- | :--- | :--- |
| **Serialization** | **Protocol Buffers (gRPC)** | 40% smaller payload, faster parsing than JSON. Strict typing. |
| **Transport** | **HTTP/2 (gRPC)** | Multiplexing, header compression, bidirectional streaming. |
| **Reliability** | **Idempotency Keys** | Prevent duplicate processing on retries. Key = `user_id + timestamp + hash(payload)`. |
| **Resilience** | **Dead Letter Queue (DLQ)** | Failed messages move to DLQ for inspection/replay instead of being lost. |
| **Flow Control** | **Token Bucket Rate Limiter** | Prevents cascade failures during traffic spikes. |

### Implementation Snippet: Idempotent Message Handler
```python
# infrastructure/messaging/handler.py
async def handle_message(msg: MessageProto, idempotency_key: str):
    if await redis.exists(f"idemp:{idempotency_key}"):
        return await redis.get(f"result:{idempotency_key}")
    
    async with redis.lock(f"lock:{idempotency_key}", timeout=5):
        # Double check after lock acquisition
        if await redis.exists(f"idemp:{idempotency_key}"):
            return await redis.get(f"result:{idempotency_key}")
        
        try:
            result = await process_business_logic(msg)
            await redis.setex(f"idemp:{idempotency_key}", 3600, "processed")
            await redis.setex(f"result:{idempotency_key}", 3600, result)
            return result
        except Exception as e:
            await send_to_dlq(msg, str(e))
            raise
```

---

## 3. Specialized Pipelines

### A. Meal Analysis Pipeline
**Goal:** Accurate nutritional tracking from text or images.

**Flow:**
1.  **Input:** Image (JPEG/PNG) or Text Description.
2.  **Preprocessing:** Image resizing, normalization.
3.  **Vision Model (Async Worker):** 
    - Use **CLIP** or **Food-101** fine-tuned model for food classification.
    - Estimate portion size using reference objects (plate/cutlery detection).
4.  **Nutrition Lookup:** Query USDA FoodData Central API for macros/micros.
5.  **Confidence Check:** 
    - If `confidence < 0.8`, trigger **Clarification Agent**: "Did this meal include dressing or oil?"
6.  **Output:** Structured `MealLog` entity saved to DB.

### B. Emotion Analysis & Mood-Adaptive Engine
**Goal:** Empathetic, context-aware responses and crisis detection.

**Pipeline:**
1.  **Real-time Stream:** Every user message passes through a lightweight sentiment analyzer (e.g., DistilBERT).
2.  **Metrics:** 
    - `Valence` (Positive/Negative)
    - `Arousal` (Calm/Excited)
    - `Distress_Score` (0.0 - 1.0)
3.  **Feature: Mood-Adaptive Response:**
    - **High Distress:** Switch persona to "Supportive Counselor". Shorten sentences. Validate feelings. Offer resources.
    - **Low Energy:** Switch to "Motivational Coach". Encouraging tone.
4.  **Safety Trigger:** If `Distress_Score > 0.9` AND keywords (suicide, harm) detected → **Immediate Human Escalation Protocol**.

### C. Medication Parsing + OCR + Reminders
**Goal:** Zero-friction medication setup from photos.

**Architecture:**
1.  **Upload:** User sends image to `/api/v1/medications/scan`.
2.  **OCR Service (Worker):** 
    - Pre-process image (binarization, deskewing).
    - Run **EasyOCR** or **Google Vision API**.
3.  **NER Extraction:** 
    - Pass raw text to a fine-tuned **BioBERT** model.
    - Extract: `[Drug_Name, Dosage, Frequency, Route, Duration]`.
4.  **Validation:** 
    - Check against drug interaction database.
    - Verify dosage ranges.
5.  **User Confirmation:** Return JSON draft to UI for user approval.
6.  **Scheduler:** On confirm, create recurring jobs in **Reminder Engine**.

---

## 4. Reminder System Refactoring

### Current Limitations
- Reliance on simple `asyncio.sleep` or basic cron.
- No handling for timezone changes or missed doses.
- Lack of multi-channel support.

### New Design: Distributed Smart Scheduler
**Tech Stack:** Redis Streams + APScheduler (or Celery Beat).

**Features:**
1.  **Smart Rescheduling:** 
    - If user misses a dose by >30 mins, analyze historical adherence. 
    - If usually late, nudge again in 15 mins. If usually strict, mark as missed and log.
2.  **Context-Aware Delivery:** 
    - Do not send reminders if `User.status == "sleeping"` (inferred from activity/emotion).
3.  **Unified Notification Interface:**
    ```python
    class NotificationPort(ABC):
        async def send(self, user_id: str, message: str, channel: ChannelType):
            pass

    class PushAdapter(NotificationPort): ...
    class SMSAdapter(NotificationPort): ...
    ```
4.  **Feedback Loop:** Track `opened_at`, `dismissed_at`, `snoozed_duration` to optimize future timing using RL (Bandits).

---

## 5. Integration Roadmap (16 Weeks)

### Phase 1: Foundation & Stability (Weeks 1-4)
- [ ] **Refactor:** Implement Hexagonal boundaries for `Medication` and `Meal` domains.
- [ ] **Infra:** Set up gRPC scaffolding and Protobuf definitions.
- [ ] **Reliability:** Implement Idempotency middleware and DLQ.
- [ ] **Pipeline:** Build MVP OCR pipeline (Text-only input first).

### Phase 2: Intelligence & Pipelines (Weeks 5-8)
- [ ] **Vision:** Integrate Food Recognition model and USDA API.
- [ ] **Emotion:** Deploy Sentiment Analysis microservice.
- [ ] **Logic:** Implement Mood-Adaptive Response rules engine.
- [ ] **Scheduler:** Migrate reminders to Redis-based distributed scheduler.

### Phase 3: Optimization & RL (Weeks 9-12)
- [ ] **Latency:** Optimize Context Pruning to <15ms.
- [ ] **RL:** Deploy Contextual Bandits for reminder timing optimization.
- [ ] **Testing:** Load test entire pipeline to verify <100ms P95.

### Phase 4: Production Hardening (Weeks 13-16)
- [ ] **Security:** Audit family permission scopes and data isolation.
- [ ] **Observability:** Full tracing with OpenTelemetry (Trace OCR -> LLM -> DB).
- [ ] **Rollout:** Canary deployment of new architecture.

---

## 6. Recommended Tech Stack Updates

| Area | Current/Legacy | Recommended Replacement | Reason |
| :--- | :--- | :--- | :--- |
| **IPC** | JSON/REST | **gRPC + Protobuf** | Latency, Type Safety, Streaming |
| **OCR** | Tesseract (Basic) | **EasyOCR / Google Vision** | Higher accuracy on curved labels |
| **NLP** | Generic LLM | **BioBERT (Fine-tuned)** | Domain specificity for meds |
| **Scheduler** | Asyncio/Cron | **Redis + Celery Beat** | Persistence, Distributed locking |
| **Vector DB** | In-Memory | **Qdrant / Milvus** | Scalability, HNSW indexing |
| **Config** | Env Vars | **Vault / AWS Secrets** | Dynamic config, Rotation |

---

## 7. Immediate Action Items
1.  **Create `src/care_pilot/core/interfaces`**: Define strict contracts for all external services.
2.  **Prototype gRPC Service**: Convert one internal call (e.g., `get_user_profile`) to gRPC to benchmark latency gains.
3.  **Dataset Collection**: Gather 500+ images of medication bottles and meal plates for fine-tuning/validation.
4.  **Define Schema**: Update DB schema to support `emotion_scores` and `reminder_feedback` tables.
