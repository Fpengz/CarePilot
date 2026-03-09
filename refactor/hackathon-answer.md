# Hackathon Answer

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

## 3 Signature User Journeys

## Journey 1: The Hawker Meal Moment

User snaps lunch at a hawker centre or types:

- "Can eat or not?"

The system:

1. identifies the meal and likely components
2. matches it against the patient’s condition and medication context
3. gives a realistic safer option
4. explains why in plain language
5. logs the meal into the daily context

Wow factor:

- local food understanding
- practical advice
- culturally believable behavior change

## Journey 2: The Quiet Relapse Rescue

The user has several high-risk meals, stops engaging, and misses medication.

The system:

1. detects the pattern
2. recognizes that generic reminders are failing
3. changes tone and timing
4. offers one small achievable action
5. escalates to caregiver only if the consented threshold is crossed

Wow factor:

- proactive and empathetic
- not just reminder spam
- feels like a companion, not a dashboard

## Journey 3: The Clinician Snapshot

Before an appointment or at escalation time, the system generates a concise digest:

- trend changes
- diet pattern summary
- adherence issues
- emotional friction signals
- suggested intervention priorities

Wow factor:

- bridges patient life and clinical workflow
- reduces administrative burden
- gives the clinician a better starting point

## The Clinician Workflow

The clinician experience should be simple:

1. receive only the patients who cross a threshold
2. view a 30-second digest
3. see risk level, top changes, likely barriers, and suggested action
4. act without reading long conversations

The key claim is:

- we do not create more clinician work
- we compress messy daily patient reality into an actionable summary

## What Is Uniquely Singaporean

- understands hawker meals, not generic “Asian food”
- supports Singlish and mixed-language interaction
- adapts advice to realistic local substitutions
- can support family and caregiver patterns common in local households
- designed around everyday food decisions, not only clinic moments

## Why We Can Win

This concept balances all four judging dimensions:

- `impressive demo`
  because meal understanding + personalization + proactive follow-up is visible and memorable
- `real-world impact`
  because it solves daily adherence and decision-making problems
- `technical depth`
  because it integrates multimodal input, retrieval, personalization, safety, and longitudinal workflows
- `clinical credibility`
  because deterministic safety and clinician digests make it feel deployable

## Judge-Facing Summary

If the judges ask what is novel, the answer is:

- not just detecting food
- not just giving advice
- not just reminding

The novelty is the combination:

- localized meal understanding
- proactive behavior support
- multi-source personalization
- clinician-friendly summarization
- measurable outcomes

## Suggested 90-Second Pitch

"Dietary Guardian SG is an AI health companion built for real life in Singapore. It understands what a patient actually eats at hawker centres, reads their reports, tracks their behavior over time, and gives culturally realistic guidance instead of generic wellness advice. It moves beyond passive reminders by proactively detecting risky patterns, adapting its tone when patients disengage, and escalating only when needed. For clinicians, it turns noisy daily behavior into concise action-oriented digests. And because it measures adherence, meal-risk trends, and intervention effectiveness, we can show not just that the AI is impressive, but that it actually improves care."

## Suggested Demo Order

1. hawker meal photo or text input
2. personalized safer recommendation
3. evidence-backed explanation
4. proactive follow-up after repeated risky behavior
5. clinician digest
6. impact dashboard

## What To Emphasize In Q&A

- safety is deterministic first
- advice is culturally realistic, not generic
- personalization uses multiple signals, not just profile text
- clinician burden is reduced, not increased
- impact is measured with concrete metrics
