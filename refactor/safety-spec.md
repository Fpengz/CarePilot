# Safety Specification

## Purpose

Define the safety model for the clean-slate consumer health guidance platform.

This document is intentionally stricter than the product experience. Safety is not an add-on. It is the system boundary that determines what the platform is allowed to say and do.

## Safety Goals

- prevent dangerous under-reaction to urgent symptoms
- prevent unsupported medical claims
- prevent overconfident or clinician-like language beyond policy
- prevent unsafe medication and contraindication guidance
- preserve user trust through consistent escalation behavior
- make every high-impact decision auditable

## Safety Model

The platform uses layered safety:

1. deterministic policy checks
2. model-assisted ambiguity review
3. final response authorization
4. post-hoc evaluation and replay

## Risk Tiers

### `low`

Examples:

- general education
- habit support
- meal logging help
- generic prevention content

### `medium`

Examples:

- personalized but non-urgent guidance
- symptom clarification
- behavior recommendations tied to known conditions
- adherence coaching where no urgent warning exists

### `high`

Examples:

- urgent-sounding symptoms
- medication safety questions
- vulnerable-user context
- repeated deterioration signals
- advice that could plausibly delay medical attention

### `critical`

Examples:

- emergency red flags
- self-harm or severe distress signals if in scope
- chest pain, trouble breathing, fainting, stroke-like symptoms
- severe allergic reaction indicators

Critical responses are not normal coaching turns. They require strict escalation behavior.

## Safety Pipeline

### Stage 1: Pre-Agent Deterministic Screening

Always run before any reasoning agent:

- emergency keyword and symptom detection
- severe medication contraindication checks
- age and vulnerable-user gating
- unsupported request category checks
- consent and privacy constraints

If a hard block or hard escalation is triggered here, the normal agent path is bypassed.

### Stage 2: Candidate Generation

Capabilities and agents may generate structured proposals, but they do not have delivery authority.

### Stage 3: Safety Review

The Safety and Policy Service evaluates:

- urgent symptom likelihood
- claim support quality
- confidence and uncertainty handling
- recommendation scope
- instruction severity
- need for follow-up questions
- need for clinician or emergency escalation

The SafetyReviewAgent may assist when the situation is ambiguous, but deterministic policy remains authoritative.

### Stage 4: Final Authorization

Possible decisions:

- `allow`
- `allow_with_downgrade`
- `replace_with_safe_template`
- `require_clinician_escalation`
- `require_emergency_escalation`
- `block`

### Stage 5: Trace and Replay

Every safety decision must emit:

- policy version
- relevant rule IDs
- evidence sufficiency grade
- escalation outcome
- final response mode

## Safety Rule Families

### Symptom Escalation Rules

Policy types:

- immediate emergency escalation
- same-day clinician escalation
- ask-more-questions before advice
- allow education only

These rules should support:

- symptom combinations
- severity markers
- time progression
- condition-aware modifiers
- medication-aware modifiers

### Advice Scope Rules

These control whether the platform can:

- educate only
- recommend self-monitoring
- recommend routine follow-up
- recommend urgent care or emergency care
- suggest lifestyle changes within policy

The system must not present unsupported interventions as personalized treatment directives.

### Evidence Sufficiency Rules

Every recommendation should receive an evidence sufficiency classification:

- `strong`
- `adequate`
- `weak`
- `insufficient`

If evidence is `insufficient`, the platform may:

- ask follow-up questions
- provide generic education only
- decline specific guidance

### Medication and Contraindication Rules

The platform must use deterministic knowledge for:

- known drug interactions in approved scope
- contraindication warnings
- reminder safety logic
- duplicate-therapy suspicion if in scope

High-risk medication guidance should default toward escalation or conservative educational framing.

### Vulnerable User Rules

Examples:

- minors
- pregnancy context if in scope
- cognitively vulnerable users
- caregiver-mediated sessions

These flows require narrower policy envelopes and stronger escalation behavior.

## Response Modes

Every delivered response must have one of the following modes:

- `education_only`
- `guidance`
- `guidance_with_follow_up`
- `monitor_and_check_back`
- `seek_routine_care`
- `seek_urgent_care`
- `seek_emergency_care`
- `blocked`

The frontend and analytics stack should consume this mode explicitly.

## Human and External Escalation

Escalation targets may include:

- emergency services guidance
- same-day clinician recommendation
- future internal care navigator queue
- caregiver notification if consented

The platform should distinguish:

- `recommend escalation`
- `trigger internal escalation workflow`
- `notify authorized caregiver`

These are different actions and must not be conflated.

## Allowed Agent Roles in Safety

Allowed:

- ambiguity review
- contradiction detection
- unsafe tone detection
- support for ranking uncertain concerns

Not allowed:

- overriding deterministic hard blocks
- inventing new policy classes
- mutating durable risk state directly

## Safety Telemetry

Required counters and traces:

- responses by risk tier
- emergency escalations by trigger
- downgrade rate
- unsupported-claim block rate
- false-positive review rate
- false-negative incident count
- policy decision latency

## Release Gates

No policy or model release should ship without:

- offline regression suite pass
- red-flag scenario suite pass
- unsupported-claim suite pass
- replay against sampled historical traces
- documented diff in policy behavior

## Incident Review Package

For any harmful or near-harmful event, the incident package must include:

- case snapshot at decision time
- retrieved evidence
- capability outputs
- agent outputs
- policy decisions
- final response
- workflow timeline
- owning model and policy versions

## Engineering Constraints

- safety rules are versioned artifacts
- policy decisions are persisted records
- emergency behavior is deterministic-first
- agents can advise safety review but cannot own it
