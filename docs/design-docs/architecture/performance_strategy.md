# CarePilot Performance Strategy: Fast-Path & Context Pruning

## 1. Fast-Path Intent Gate

### Problem
Expensive `CaseSnapshot` and `LangGraph` logic run for simple social messages.

### Strategy
Implement a "Level 0" classifier in `ChatOrchestrator`.

1. **Regex Classifier**: Handle `[meal]:`, `log meal:`, and basic greetings.
2. **FastIntentClassifier**: A lightweight LLM call (e.g., using `GPT-4o-mini` or `Gemini 1.5 Flash`) with a simple binary prompt.
    - *Is this message a low-intent social greeting or a generic thank you? (Yes/No)*

### Implementation Path
```python
# src/care_pilot/features/companion/chat/orchestrator.py

async def stream_events(...):
    # 0. Fast-Path Check
    if await is_low_intent(user_message):
        yield ChatStreamEvent(event="token", data={"text": "Hello! How can I help you today?"})
        return
        
    # Proceed to full logic only if high-intent...
```

## 2. Context Pruning Layer

### Problem
Large `CaseSnapshot` objects increase LLM token costs and latency.

### Pruning Rules
1. **Activity Window**:
    - Keep only the last 3 days of *all* activity in full detail.
    - Keep days 4-14 as a **summarized projection** (e.g., "3 high-sodium meals, 100% medication adherence").
2. **Relevance Filter**:
    - If user asks about "Laksa", include *all* high-sodium hawker meals from the last 14 days, but prune medication data older than 1 day.
    - If user asks about "Metformin", include all medication adherence, but prune meal data.
3. **Pydantic Optimization**:
    - Use `exclude_unset=True` or field-specific masks during `model_dump_json` to only send what the agent needs.

### Implementation Path
```python
# src/care_pilot/features/companion/core/snapshot.py

def build_case_snapshot(...):
    # Apply pruning rules here based on query intent
    pruned_meals = prune_irrelevant_meals(meals, intent)
    ...
```
