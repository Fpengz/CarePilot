# CarePilot Dev Harness

## 1. Task

Refactor the database, including the tables and columns defined. Make sure each column are defined under the right tables. And make sure the database system architecture is robust. 

---

## 2. Goal

* this refactor should try to address the technical debt caused during hackathon development, such as in memory storage, wrong columns under inappropriate tables.
* You should try to design the tech stack first, including the integration with memory layer, RAG layer, message channels, backend workers, frontend data pipeline, future data analysis, latency, end-to-end pipeline safety and robustness, personalisation features, user profiles, etc. The database is the backbone of this system, so we need to get it perfectly suitable for the system and functioning as intented. 
* should als consider for future scale and maintainance.
* use docs/subfolder to keep your change logs, updates etc. 

---

## 3. Scope

* Basically every modules, especially modules mentioned in the Goal section. 

### Non-Goals

* In this plan, no UI design should be altered.

---

## 4. Invariants (Must NOT Break)

* Route handlers remain thin (no business logic)
* All outputs are typed (Pydantic schemas)
* No direct model/provider calls from transport layer
* State changes remain auditable (timeline events)
* Safety-critical flows (medication/reminders) are NOT auto-committed
* Ensure all tests are green after each checkpoints and the final step.

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

1. try to use writing plans and brainstorm skills to break this into checkpointed steps. 
2. use systemetic debugging and test-driven development during development

---

## 7. Validation Plan

* Lint / format
* Type check
* Unit tests
* Integration tests (if applicable)
* Schema validation
* Manual scenario test:

Example:
* ensure the scripts/cli.py are updated accordingly. 

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

