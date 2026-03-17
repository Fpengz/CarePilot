# LLM Prompt Catalog

This document provides a comprehensive catalog of the Large Language Model (LLM) prompts used throughout the CarePilot system.

## 1. Core Agent Prompts

| Prompt Name | Capability | Model | Input | Output | Prompt Template (Snippet) | File Location |
|-------------|------------|------|------|-------|----------------|---------------|
| chat_system_prompt | Conversational AI | GPT-4o / SEA-LION | User query + History | Conversational Text | "You are SEA-LION, a helpful health assistant specialised in Singapore's food..." | `agent/chat/agent.py` |
| meal_perception_prompt | Computer Vision | GPT-4V / Gemini Pro Vision | Meal Image | Structured `MealPerception` JSON | "You are the 'Hawker Vision' Expert... Detect likely foods, component count..." | `agent/meal_analysis/meal_perception_agent.py` |
| dietary_reasoning_prompt | Dietary Guidance | GPT-4o | Meal details + Health Goals | Structured Singlish Guidance | "You are 'Uncle Guardian'. You are a retired hawker... tone is warm, Singlish..." | `agent/dietary/agent.py` |

## 2. Feature-Specific Prompts

| Prompt Name | Capability | Model | Input | Output | Prompt Template (Snippet) | File Location |
|-------------|------------|------|------|-------|----------------|---------------|
| medication_parse_prompt | Prescription Ingestion | GPT-4o | Raw instruction text | Structured Medication JSON | "You extract structured medication instructions... Each object must contain: name, dose..." | `features/medications/intake/parser.py` |
| chat_classification_prompt | Query Routing | GPT-4o-mini | User message | Route Label (drug, food, code, general) | "Classify the user's message into EXACTLY ONE of these four categories..." | `features/companion/chat/router.py` |
| patient_card_prompt | Clinical Synthesis | GPT-4o | Case Snapshot + Evidence | Markdown Medical Card | "Based on the following patient summary and medical references, generate a concise..." | `features/companion/patient_card/patient_card_service.py` |
| memory_summary_prompt | Personalization | GPT-4o-mini | Chat turns | Personalized Memory Snippets | "Summarize the key health-related information from this conversation..." | `features/companion/chat/memory.py` |

## 3. RAG and Evidence Prompts

*   **Retrieval Query Generation:** Used in `evidence_service.py` to transform patient context into search queries for clinical databases (e.g., PubMed, local guidelines).
*   **Grounding Instructions:** Embedded in the `patient_card_prompt` and `chat_system_prompt` to ensure AI responses are grounded in provided evidence snippets.
*   **Citation Format:** The system enforces a strict citation format (Title + Summary + URL) to maintain clinical transparency.

## 4. Prompt Design Observations

*   **Personality Consistency:** The use of "Uncle Guardian" and "SEA-LION" personas helps maintain a consistent, culturally relevant tone for Singaporean users.
*   **Schema Enforcement:** Most feature-level prompts use strict JSON schemas via `pydantic-ai`, ensuring that the outputs are always machine-readable.
*   **Context Injection:** The "Case Snapshot" pattern efficiently injects a holistic view of the patient into various prompts, reducing redundancy.
*   **Redundancy:** There is some overlap between "SEA-LION" (general chat) and "Uncle Guardian" (dietary guidance). These could be standardized into a single "CarePilot" persona with specialized modules.

## 5. Recommended Prompt Architecture

*   **Centralized Prompt Registry:** Move all raw prompt strings to a dedicated `src/care_pilot/core/prompts/` directory or a database for better versioning.
*   **Prompt Testing Pipeline:** Implement automated tests that run specific prompts against "golden datasets" to catch regressions in reasoning or extraction.
*   **Dynamic Context Pruning:** Implement more sophisticated logic to prune the "Case Snapshot" based on the query classification, saving tokens and improving focus.
