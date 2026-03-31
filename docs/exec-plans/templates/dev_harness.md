# CarePilot Dev Harness

## 1. Task

[One clear sentence describing the task]

---

## 2. Goal

* What does success look like?
* What user/system outcome improves?

---

## 3. Scope

* [Files / modules to touch]
* [Flows affected]

### Non-Goals

* [What we explicitly will NOT do]
* [What is deferred]

---

## 4. Invariants (Must NOT Break)

* Route handlers remain thin (no business logic)
* All outputs are typed (Pydantic schemas)
* No direct model/provider calls from transport layer
* State changes remain auditable (timeline events)
* Safety-critical flows (medication/reminders) are NOT auto-committed
* Background jobs remain idempotent

(Add task-specific invariants below)

* [...]

---

## 5. Acceptance Criteria

* [ ] Feature works for main scenario
* [ ] Edge cases handled or explicitly blocked
* [ ] Output schema validated
* [ ] No regression in existing flows
* [ ] Logs / events correctly emitted

---

## 6. Plan (Checkpointed Steps)

1. [Step 1: small, testable]
2. [Step 2]
3. [Step 3]
4. [Step 4]
5. [Step 5]

---

## 7. Validation Plan

* Lint / format
* Type check
* Unit tests
* Integration tests (if applicable)
* Schema validation
* Manual scenario test:

Example:

* Input:
* Expected:
* Actual:

---

## 8. Execution Log (Fill During Work)

### Step 1

* What was done:
* Result:
* Issues:

### Step 2

* What was done:
* Result:
* Issues:

(...)

---

## 9. Validation Results

* Lint: PASS / FAIL
* Types: PASS / FAIL
* Tests: PASS / FAIL
* Schema: PASS / FAIL
* Manual scenario: PASS / FAIL

---

## 10. Gap Analysis

* What still feels fragile?
* What edge cases are missing?
* What coupling was introduced?
* What assumptions are implicit?

---

## 11. Decision Log

* What was changed:
* Why this approach:
* Alternatives considered:
* Tradeoffs:

---

## 12. Risks / Tech Debt

* [...]
* [...]

---

## 13. Next Tasks (Concrete, Bounded)

* [Next small task]
* [Next improvement]
* [Next fix]

---

## 14. Notes (Optional)

* Observations
* Ideas for future refactor

