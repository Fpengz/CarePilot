# PydanticAI Multi-Agent Patterns

## Purpose

Map the multi-agent strategies described in the PydanticAI documentation to the proposed consumer health platform design in this repository.

This document answers a practical question:

- which PydanticAI multi-agent patterns should this system actually use
- where should each pattern apply
- which patterns should be avoided for the hackathon

## Source Frame

This document is based on the PydanticAI multi-agent applications guidance and adapts it to the platform defined in:

- `system-architecture.md`
- `service-contracts.md`
- `safety-spec.md`
- `execution-plan.md`

## Recommendation Summary

### Use by Default

- `Programmatic agent hand-off`

### Use Selectively

- `Agent delegation`
- `Graph-based control flow`

### Avoid for This System

- `Deep Agents`

### Mandatory Across All Patterns

- `Observability and tracing`

## Pattern 1: Programmatic Agent Hand-Off

### What It Means

Application code decides which agent runs next.

The model does not decide the overall control flow.

### Why This Should Be the Default

This pattern best matches the proposed architecture:

- gateway receives request
- care orchestrator loads case state
- deterministic capability checks run
- application code invokes specific agents
- safety review is explicitly invoked
- application code commits state and emits events

This is the safest and most legible model for a health-adjacent product because:

- routing stays deterministic
- safety remains external to prompts
- workflows remain visible in code
- durable state changes do not depend on LLM discretion

### Where To Use It

- main synchronous chat or interaction path
- meal photo review entry
- meal text or voice entry
- report explanation entry
- weekly check-in entry
- evidence-backed guidance generation
- final safety review before delivery

### Example Mapping

1. Care Orchestrator calls `IntentContextAgent`
2. Care Orchestrator examines typed intent
3. Care Orchestrator calls `CarePlanningAgent`
4. Care Orchestrator may call `EvidenceSynthesisAgent`
5. Care Orchestrator runs deterministic policy review
6. Care Orchestrator calls `SafetyReviewAgent` only when policy marks the case as ambiguous
7. Care Orchestrator persists state and returns response

### Recommendation

This should be the default orchestration style for the hackathon and likely remain the default long term.

## Pattern 2: Agent Delegation

### What It Means

One agent delegates a subtask to another agent and then regains control.

### Why It Can Help

This is useful when one reasoning step naturally depends on a second specialized reasoning step.

Examples:

- care planning needs a patient-friendly evidence explanation
- care planning needs motivational framing
- evidence synthesis needs simplification for reading level or language tone

### Where To Use It

Use only for low- or medium-risk synthesis subtasks such as:

- `CarePlanningAgent -> EvidenceSynthesisAgent`
- `CarePlanningAgent -> MotivationalSupportAgent`

### Where Not To Use It

Do not use delegation for:

- workflow routing
- state transitions
- policy decisions
- escalation decisions
- final response authorization

These must remain in application code or the safety service.

### Recommendation

Use narrow delegation only if it reduces prompt complexity.

Do not let delegation become the main control plane.

## Pattern 3: Graph-Based Control Flow

### What It Means

Model the flow as an explicit state graph with nodes, branches, and resumable progression.

### Why It Can Help

This pattern becomes valuable when interactions are:

- multi-step
- branch-heavy
- resumable
- human-in-the-loop
- long-lived across multiple messages

### Best Use Cases in This System

- symptom triage sequence
- chronic-care check-in workflow
- medication adherence recovery flow
- escalation follow-up flow
- caregiver notification and response flow

### Why Not Use It Everywhere

Most user interactions do not require graph orchestration.

For a simple guidance turn, graph semantics add complexity without enough value.

### Recommendation

For the hackathon:

- use explicit Python orchestration or a simple state machine first

Later:

- introduce graph-based orchestration only for workflows that clearly benefit from resumability and branch control

If adopted, graph control should sit above agents and below the care orchestrator, not replace the whole platform design.

## Pattern 4: Deep Agents

### What It Means

Highly autonomous agents with planning, long-horizon tool use, broad task execution, and more freedom to decide how work proceeds.

### Why This Is the Wrong Pattern Here

This consumer health platform needs:

- clear control boundaries
- explicit safety review
- typed state transitions
- deterministic policy ownership

Deep agents encourage:

- too much autonomy
- less predictable control flow
- harder incident analysis
- higher safety risk

### Recommendation

Do not use deep agents for this product.

This is especially true for the hackathon.

## Pattern 5: Observability and Tracing

### What It Means

Multi-agent systems require explicit traces for:

- which agent ran
- what input it received
- what output it produced
- what tools it used
- how long it took
- what it cost
- what application code did with the result

### Why It Is Mandatory Here

Without observability, multi-agent systems quickly become un-debuggable.

For this platform, observability is also required for:

- safety review
- evidence traceability
- incident analysis
- prompt and policy iteration

### Minimum Required Trace Artifacts

- `request_id`
- `correlation_id`
- `workflow_id`
- `agent_run_id`
- `prompt_version`
- `model_version`
- `tool_calls`
- `policy_decision_id`
- `evidence_ids`

### Recommendation

Treat observability as a non-optional platform feature from day one.

## Pattern-to-Agent Mapping

### `IntentContextAgent`

Recommended pattern:

- programmatic hand-off

Why:

- app code should decide what happens after intent classification

### `CarePlanningAgent`

Recommended pattern:

- programmatic hand-off
- optional narrow delegation

Why:

- plan generation is central, but may benefit from delegated evidence or tone synthesis

### `EvidenceSynthesisAgent`

Recommended pattern:

- called directly by orchestrator
- or delegated from care planning in narrow cases

Why:

- supports grounded explanation rather than platform control

### `MotivationalSupportAgent`

Recommended pattern:

- delegated helper or direct orchestrator call

Why:

- useful for tone and adherence framing, but should not own workflow logic

### `SafetyReviewAgent`

Recommended pattern:

- direct explicit invocation only, and only after deterministic policy review flags ambiguity

Why:

- safety must be independently called and independently auditable
- deterministic policy remains the primary decision-maker
- never hide safety review behind another agent's delegation chain

## Recommended Hackathon Configuration

Use these patterns:

- `Programmatic hand-off` as the main architecture
- `Selective delegation` for evidence and tone subtasks only
- `Simple state-machine or graph flow` for symptom and check-in workflows only
- `Full tracing` for every agent run

Avoid:

- deep agents
- model-decided routing
- agent-owned state transitions
- agent-owned policy exceptions

## Final Recommendation

If the team wants a simple rule:

- let `code` own routing
- let `agents` own narrow reasoning
- let `workflows` own long-lived progression
- let `policy` own safety

That is the correct way to use PydanticAI multi-agent patterns in this system.
