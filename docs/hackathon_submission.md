# AI Health Companion — Hackathon Submission (Singapore Innovation Challenge)

## 1. Problem
In Singapore, chronic diseases like diabetes and hypertension are on the rise, placing a significant burden on the healthcare system and individuals. While patients are advised to manage their diet and medications, the transition from clinical advice to daily self-care is fraught with friction.
*   **The "Hawker Hurdle":** Singaporeans love hawker food, but it's notoriously difficult to track nutrition in complex, multi-ingredient local dishes.
*   **Adherence Fatigue:** Keeping up with multiple medications and biomarker check-ins is mentally exhausting, leading to "notification blindness" and missed doses.
*   **The Guidance Gap:** Generic health apps don't understand the Singaporean context—they don't know what "Kopi C Kosong" is or how a "Nasi Lemak" affects a diabetic patient differently than a standard meal.

## 2. Our Solution: CarePilot
CarePilot is not just a tracker; it’s an **AI-powered health companion** that speaks the language of Singaporeans. It empowers patients through:
*   **Culturally-Aware Vision:** Identifying local dishes with precision and normalizing them against a canonical hawker nutrition database.
*   **Uncle Guardian Persona:** An AI assistant that uses Singlish and a warm, empathetic tone to provide guidance that feels like it’s coming from a trusted neighbor, not a cold machine.
*   **Proactive Care Loops:** A system that doesn't wait for the patient to ask. It detects risks in real-time—like a missed pill or a high-sodium meal—and intervenes with actionable advice.

## 3. How It Works
1.  **Capture:** The patient snaps a photo of their lunch (e.g., Char Kway Teow).
2.  **Perceive:** The `MealPerceptionAgent` identifies the dish and portions.
3.  **Analyze:** The system normalizes the data and calculates the risk score based on the patient's specific conditions (e.g., Type 2 Diabetes).
4.  **Engage:** "Uncle Guardian" pops up in chat: *"Aiyah Uncle! That Char Kway Teow looks good but very oily leh. Maybe next meal take it easy on the rice, can lah?"*
5.  **Remind:** The system syncs with the patient's medication regimen and ensures they never miss a dose, adjusting reminders based on their actual meal times.
6.  **Synthesize:** Longitudinal data is compressed into a "Clinical Digest" for their next doctor's visit.

## 4. Technical Architecture
*   **Modular Monolith:** Built for extensibility and strict feature ownership.
*   **Agent Orchestration:** Uses `pydantic-ai` for bounded reasoning and `pydantic-graph` for complex health workflows.
*   **Multimodal Inference:** Combines vision, text, and speech models to understand the patient holistically.
*   **Local-First Data:** Uses SQLite for fast, reliable local storage, ensuring patient data is always accessible.

## 5. Demonstration Scenario
*   **08:00 AM:** CarePilot sends a gentle reminder for Metformin.
*   **12:30 PM:** Patient uploads a photo of Laksa. The AI detects high sodium and logs it.
*   **03:00 PM:** AI detects the patient hasn't logged water intake today. Uncle Guardian sends a nudge: *"Uncle, drink some water lah, don't just drink kopi!"*
*   **07:00 PM:** Patient records a voice note about feeling dizzy. The `EmotionAgent` detects high stress/concern, and the system immediately generates a BP check-in request.

## 6. Innovation Highlights
*   **Local Food Specialization:** A dedicated vision-to-normalization pipeline for the Singapore hawker ecosystem.
*   **The "Case Snapshot" Pattern:** Ensuring all AI reasoning is grounded in a unified, cross-feature view of the patient's history.
*   **Persona-Driven Adherence:** Moving beyond "pings" to "conversations" that build trust and long-term habits.

## 7. Impact
*   **For Patients:** Reduced anxiety through personalized, culturally-relevant guidance.
*   **For Caregivers:** Peace of mind knowing their loved ones are being looked after by a proactive system.
*   **For the Healthcare System:** Improved medication adherence and dietary control, leading to fewer hospital readmissions and better chronic disease outcomes for Singapore.

## 8. Future Vision
We aim to integrate CarePilot directly with **HealthHub and the National Electronic Health Record (NEHR)**, allowing for seamless data flow between patients and their healthcare providers. Our long-term goal is to use longitudinal health modeling to predict and prevent health crises before they happen, making Singapore a world leader in AI-driven preventative care.
