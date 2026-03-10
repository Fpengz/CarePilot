# Hackathon Answer

This document is the judge-facing narrative for the hackathon. It is intentionally pitch-oriented.

Engineering source of truth remains:
- `README.md`
- `ARCHITECTURE.md`
- `SYSTEM_ROADMAP.md`
- implemented code and tests

## One-Line Pitch

Dietary Guardian SG is a Singapore-native AI health companion that understands what patients eat, how they feel, what their reports show, and when clinicians should intervene, then turns that into safe, proactive, and culturally relevant guidance.

## The Core Story

Most health companions are passive. They wait for the user to ask a question or respond to a reminder.

Our idea is different:

- it understands real daily life in Singapore
- it proactively engages before small problems become bigger ones
- it personalizes guidance using multiple data sources
- it summarizes only the most useful insights for clinicians
- it measures whether it is actually helping

This is not just a chatbot. It is a daily companion for chronic condition management and prevention.

## Why This Matters in Singapore

Singapore patients do not live inside generic wellness apps. They live in:

- hawker centres
- coffee shops
- multigenerational households
- multilingual, code-switching conversations
- high-pressure routines where health decisions happen quickly

The system is designed for this reality.

Instead of saying:

- "Avoid fried noodles"

it says:

- "You can still eat char kway teow, but ask for less oil, skip extra cockles, and stop at half the noodles if you want a safer lunch."

That is the difference between generic advice and advice people can actually follow.

## How We Answer the 4 Challenge Questions

## 1. Proactive Patient Engagement

### Our Answer

The AI companion does not only remind. It detects patterns and intervenes at the right moment.

Examples:

- repeated high-risk meals across 3 days
- missed medication or skipped logging
- worsening glucose or blood-pressure trend
- disengagement after discouraging feedback
- signs that the user is struggling emotionally or behaviorally

It then chooses:

- what to say
- when to say it
- how strong the intervention should be
- whether to involve a caregiver if consent exists

### Why This Is Better Than Passive Reminders

Passive reminder:

- "Time to take your medication."

Our proactive companion:

- "You have had two high-sodium meals in a row and your recent blood pressure trend is rising. Want a safer dinner option near what you usually eat?"

That is more useful, more empathetic, and more likely to change behavior.

### Signature Proactive Behaviors

- `meal-risk streak intervention`
  Example: before lunch, the system notices 3 days of high-sugar breakfasts and suggests one realistic swap.
- `relapse-sensitive tone adaptation`
  Example: if the user stops engaging after judgmental-feeling advice, the tone shifts to supportive coaching.
- `caregiver threshold alerts`
  Example: after consent, a caregiver gets a summary only after repeated risk or missed adherence crosses a threshold.

## 2. Hyper-Personalization of Care

### Our Answer

The system fuses multiple sources into one `personalization context`:

- meal images and meal text
- report-derived biomarkers
- observed trends
- medications and conditions
- patient-reported outcomes
- future wearable summaries
- cultural context
- language and literacy preferences

The output is not just “personalized text.” It is personalized decision logic.

### What This Looks Like in Practice

The same meal should produce different advice for:

- a healthy young adult
- an older patient with diabetes
- a patient with hypertension and kidney-risk concerns
- a caregiver shopping for a parent

It also adapts to:

- Singlish-friendly phrasing
- local food names
- realistic substitutions
- emotional state
- whether the user wants explanation or quick action

### Why This Is Hard To Fake

Most demos personalize on profile only.

Our design personalizes on:

- biology
- behavior
- culture
- recent trends
- current emotional context

That makes the guidance meaningfully different, not just cosmetically different.

## 3. Bridging the Gap Between Patient and Clinician

### Our Answer

The clinician should not read raw chat logs.

The system produces a `Clinician Digest` that answers:

- what changed
- why it matters
- how urgent it is
- what the patient has already been told
- what intervention is most likely to help

### Example Digest

Patient: Mr. Tan  
Window: last 7 days

- 4 high-sodium hawker meals
- rising morning glucose trend
- missed medication twice
- lower engagement after previous warning message
- one supportive nudge succeeded

Suggested clinician action:

- review diet adherence barriers
- confirm medication timing
- reinforce one realistic lunch strategy instead of full diet overhaul

### Why This Lowers Burden

It compresses noisy behavior into:

- trend summary
- trigger summary
- action suggestion

The clinician sees the signal, not the whole exhaust stream.

## 4. Measuring Real-World Impact

### Our Answer

We define impact at four levels:

### Patient Metrics

- medication adherence rate
- meal-risk trend
- weekly engagement rate
- biomarker trend where available
- completion of recommended follow-up actions

### Behavior-Change Metrics

- proactive nudge acceptance rate
- relapse recovery rate
- healthier substitution adoption rate
- reduction in repeated risky meals

### Clinician Metrics

- number of high-risk patients surfaced appropriately
- digest generation time
- clinician review time saved proxy
- actionability score of summaries

### Health-System Metrics

- reduced preventable escalation proxy
- reduced readmission-risk proxy
- improved workflow efficiency

### Evaluation Framework

We propose:

- `baseline vs follow-up windows`
- `patient-level and cohort-level views`
- `leading indicators` such as adherence and engagement
- `lagging indicators` such as biomarker trend and escalation frequency
- explicit acknowledgment that causality is partial in early pilots

This makes the system measurable, not just impressive.
