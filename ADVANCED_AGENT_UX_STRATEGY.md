# CarePilot Advanced Agent & UX Enhancement Strategy

This document addresses advanced agent evaluation, context management, memory architecture, UX improvements, conversational features, and family functionality optimization.

## 1. Agent Evaluation: Metrics & Frameworks

Evaluating AI agents in a healthcare context requires a multi-dimensional approach focusing on accuracy, safety, latency, and user satisfaction.

### Key Metrics

| Category | Metric | Description | Target |
| :--- | :--- | :--- | :--- |
| **Accuracy** | Hallucination Rate | % of responses containing fabricated medical facts | < 1% |
| | Intent Recognition Accuracy | % of correctly identified user intents | > 95% |
| | Entity Extraction F1 | Precision/Recall for extracting meds, symptoms, foods | > 0.90 |
| **Safety** | Safety Violation Rate | % of responses triggering safety guardrails | 0% |
| | Refusal Accuracy | % of unsafe requests correctly refused | 100% |
| **Performance** | P95 Latency | 95th percentile response time | < 800ms |
| | Token Efficiency | Output tokens / Input tokens ratio | Optimized |
| **UX** | Task Completion Rate | % of conversations resolving user intent | > 90% |
| | User Satisfaction (CSAT) | Post-interaction rating (1-5) | > 4.5 |
| | Retention Rate | Users returning within 7 days | > 60% |

### Recommended Evaluation Frameworks

1.  **RAGAS (Retrieval Augmented Generation Assessment)**
    *   **Use Case:** Evaluating the quality of retrieved health context and generated answers.
    *   **Metrics:** Faithfulness, Answer Relevance, Context Precision.
    *   **Integration:** Run offline on historical conversation logs.

2.  **Arize Phoenix / LangSmith**
    *   **Use Case:** End-to-end tracing and debugging.
    *   **Features:** Trace LLM calls, view latency breakdown, annotate spans for fine-tuning datasets.
    *   **Integration:** Add as an observer in the `companion_orchestration.py` workflow.

3.  **DeepEval**
    *   **Use Case:** Unit testing for LLMs.
    *   **Features:** Assert statements for "Is Relevant?", "Is Faithful?", "Does it contain PII?".
    *   **Example:**
        ```python
        from deepeval import assert_test
        from deepeval.metrics import GEval, FaithfulnessMetric

        def test_companion_response():
            metric = FaithfulnessMetric(threshold=0.7)
            assert_test(output=response, expected_output=ground_truth, metrics=[metric])
        ```

4.  **Human-in-the-Loop (HITL)**
    *   **Mechanism:** Flag low-confidence responses (probability < 0.6) or specific keywords (e.g., "suicide", "chest pain") for clinical review.
    *   **Tooling:** Build a simple admin dashboard for clinicians to label data, which feeds back into fine-tuning.

---

## 2. Context Pruning Layer Integration

As conversation history grows, token limits and noise become issues. A context pruning layer ensures the LLM only sees relevant information.

### Strategy: Sliding Window + Semantic Relevance

1.  **System Message (Static):** Core instructions, safety guidelines, persona.
2.  **Critical Facts (Dynamic):** Current user vitals, active medications, allergies (Always included).
3.  **Recent History (Sliding Window):** Last $N$ turns (e.g., 5 turns) to maintain immediate flow.
4.  **Semantic Search (Vector Store):** For older history, embed the current user query and retrieve top $K$ relevant past interactions from a vector DB (e.g., Qdrant, pgvector).

### Implementation Plan

Modify the `build_context` step in `apps/api/carepilot_api/services/companion_orchestration.py`:

```python
async def build_pruned_context(user_id: str, current_query: str, history: list):
    # 1. Static System Prompt
    context = [SYSTEM_PROMPT]
    
    # 2. Critical Dynamic Data (Always Fresh)
    profile = await get_user_profile(user_id)
    context.append(f"User Profile: {profile.summary()}")
    
    # 3. Recent History (Last 5 turns)
    recent_history = history[-5:] if len(history) > 5 else history
    context.extend(recent_history)
    
    # 4. Semantic Retrieval for Older Context
    if len(history) > 5:
        older_history = history[:-5]
        # Embed current query
        query_vector = await embedder.encode(current_query)
        # Retrieve top 3 relevant past exchanges
        relevant_past = await vector_store.search(
            collection_name=f"user_{user_id}_history",
            query_vector=query_vector,
            limit=3
        )
        context.append("\n--- Relevant Past Conversations ---")
        context.extend(relevant_past)
        
    return "\n".join(context)
```

---

## 3. Designing a Better Memory Layer

Move beyond simple chat history to a structured **Long-Term Memory (LTM)** system.

### Memory Architecture

1.  **Short-Term Memory (STM):** The current conversation window (handled by context pruning).
2.  **Long-Term Memory (LTM):** Persistent storage of facts, preferences, and events.
    *   **Episodic Memory:** Specific events ("User went for a run on Oct 12"). Stored as timestamped entries.
    *   **Semantic Memory:** Facts ("User is allergic to peanuts", "User prefers vegetarian meals"). Stored as key-value pairs or triples.
    *   **Procedural Memory:** Learned user patterns ("User usually logs dinner at 8 PM").

### Implementation Strategy

*   **Extraction Agent:** Run a background job after every conversation turn to extract new facts.
    *   *Input:* Conversation turn.
    *   *Output:* JSON list of `{ type: "fact" | "event", content: "...", confidence: 0.9 }`.
*   **Memory Store:** Use a hybrid database approach.
    *   **Relational (PostgreSQL):** For structured facts (Allergies, Medications).
    *   **Vector (Qdrant/pgvector):** For episodic memory retrieval.
*   **Forgetting Mechanism:** Implement decay. If a fact isn't referenced in 6 months, flag it for verification or archive it.

### Schema Example (SQL)

```sql
CREATE TABLE user_memories (
    user_id UUID,
    memory_type VARCHAR(20), -- 'semantic', 'episodic'
    content TEXT,
    embedding VECTOR(768),
    created_at TIMESTAMP,
    last_accessed_at TIMESTAMP,
    confidence_score FLOAT
);
```

---

## 4. Improving User Experience (UX)

### Visual & Interaction Enhancements

1.  **Structured Responses:** Instead of plain text, use rich UI components for specific intents.
    *   *Meal Log:* Render a card with image, calories, and macros.
    *   *Medication:* Render a checklist with dosage and timing.
2.  **Optimistic UI:** Update the interface immediately upon user action (e.g., checking a med) before the API confirms, then reconcile.
3.  **Voice First:** Integrate Web Speech API for hands-free logging (crucial for elderly or cooking scenarios).
4.  **Accessibility (a11y):**
    *   Ensure WCAG 2.1 AA compliance.
    *   High contrast modes for visually impaired.
    *   Screen reader optimized landmarks.

### Trust & Transparency

1.  **Citation Links:** When providing health advice, show small footnotes linking to sources (e.g., Mayo Clinic, CDC).
2.  **Confidence Indicators:** Subtly indicate uncertainty ("I'm not a doctor, but generally...").
3.  **Edit Capability:** Allow users to edit the AI's interpretation of their log immediately (e.g., "You logged 'Apple', did you mean 'Apple Pie'?").

---

## 5. Enhancing Chatting Experience (Feature Extraction)

Transform the chat from a Q&A bot into an **Action-Oriented Assistant**.

### Feature Pipeline

1.  **Intent Classification:** Detect if the user is logging, asking, or seeking recommendation.
2.  **Entity Extraction (NER):** Extract specific entities (Food, Meds, Symptoms, Time).
3.  **Action Triggering:** Call specific API endpoints based on intent.

### Specific Implementations

#### A. Meal Logging & Recommendations
*   **User:** "I just ate a chicken salad with ranch dressing."
*   **System Action:**
    1.  Extract: `{"item": "Chicken Salad", "extras": ["Ranch Dressing"], "time": "now"}`.
    2.  Estimate Calories (via Nutritionix API or internal DB).
    3.  **Response:** "Logged: Chicken Salad (~450 kcal). That's a great protein source! Would you like to add this to your daily log?"
    4.  **UI:** Show a "Confirm Log" button.

#### B. Medication Parsing & Reminders
*   **User:** "I need to take Metformin 500mg twice a day."
*   **System Action:**
    1.  Extract: `{"med": "Metformin", "dosage": "500mg", "frequency": "BID"}`.
    2.  **Response:** "I've set up a reminder for Metformin 500mg at 9 AM and 9 PM. Should I start today?"
    3.  **Backend:** Create cron jobs or push notification tasks.

#### C. Generated Reminders (Proactive)
*   **Logic:** Analyze patterns. If user usually logs water in the morning but hasn't today:
*   **System:** "Good morning! You usually track your water intake around now. Want to log your first glass?"

#### D. Symptom Tracking
*   **User:** "My head has been pounding since noon."
*   **System Action:**
    1.  Extract: `{"symptom": "Headache", "severity": "High", "onset": "12:00 PM"}`.
    2.  **Response:** "I've logged a severe headache starting at noon. Have you taken any pain relievers? Here are some hydration tips..."

### Technical Enabler: Structured Output
Force the LLM to output JSON for these interactions using Pydantic constraints in the orchestration layer.

```python
class LogExtraction(BaseModel):
    type: Literal["meal", "medication", "symptom", "workout"]
    items: List[str]
    timestamp: datetime
    confidence: float
```

---

## 6. Family Functionality: Validation & Brainstorming

### Current Validation Check
*Reviewing `apps/api/carepilot_api/routers/users.py` and related models.*

**Potential Gaps to Verify:**
1.  **Consent Management:** Does the system explicitly store consent records for sharing data between family members? (Critical for HIPAA/GDPR).
2.  **Role Granularity:** Are roles distinct? (e.g., "Parent" vs. "Caregiver" vs. "Read-Only Observer").
3.  **Data Isolation:** Ensure queries strictly filter by `family_id` AND `permission_level` to prevent data leakage.
4.  **Revocation:** Can a user instantly revoke access? The system must invalidate cached permissions immediately.

### Brainstorming: Better Utilization of Family Features

#### A. Collaborative Care Circles
*   **Concept:** Beyond simple "family," allow users to create "Care Circles" including doctors, nutritionists, or close friends.
*   **Feature:** Specific data views for specific roles. A nutritionist sees food logs; a doctor sees vitals and symptoms.

#### B. Shared Goals & Challenges
*   **Gamification:** "Family Step Challenge" or "Hydration Contest."
*   **Implementation:** Aggregate anonymized progress metrics. "The Smith Family walked 50k steps this week!"

#### C. Smart Alerts for Caregivers
*   **Scenario:** Elderly parent hasn't logged medication by 10 AM.
*   **Action:** Send a gentle nudge to the adult child: "Mom hasn't logged her morning meds yet. Could you give her a call?"
*   **Privacy:** Do not reveal *what* the med is, just that a routine was missed.

#### D. Unified Shopping Lists
*   **Feature:** If User A logs "Out of milk" and User B logs "Need eggs," generate a shared shopping list accessible by whoever is going to the store.
*   **Integration:** Link to Instacart or Amazon Fresh APIs.

#### E. Legacy & Emergency Access
*   **Feature:** "Break Glass" protocol. In a verified emergency (hospital admission), grant temporary full access to designated next-of-kin.

### Recommended Database Schema Update for Family

```sql
CREATE TABLE family_members (
    family_id UUID,
    user_id UUID,
    role VARCHAR(20), -- 'admin', 'caregiver', 'member', 'observer'
    permissions JSONB, -- { "view_logs": true, "edit_logs": false, "view_vitals": true }
    invited_by UUID,
    status VARCHAR(20), -- 'pending', 'active', 'revoked'
    consent_record_id UUID -- Link to signed consent form
);
```

### Next Steps for Implementation
1.  **Audit:** Run a security audit on current family permission checks.
2.  **Prototype:** Build the "Shared Goal" feature as a low-risk, high-engagement pilot.
3.  **Compliance:** Consult legal counsel on the "Care Circle" expansion for HIPAA implications.
