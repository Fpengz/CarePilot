## Revised TODOs (Problem + Solution Approach)

  1. Account‑scoped chat/meal/everything memory is leaking across users
     Problem: Chat memory appears global or session‑only, not tied to
     authenticated user IDs.
     Solve:

  - Introduce user_id scoping in MemoryManager and the persistence layer
    (table/schema key).
  - Ensure API routes pass user_id into memory calls.
  - Add tests for cross‑user isolation.
     Status: DONE (MemoryManager and HealthTracker are user/session scoped; tests exist).

  2. Food normalization database missing or incomplete
     Problem: Meal normalization lacks a canonical food dictionary.
     Solve:

  - Define a canonical food normalization dataset format.
  - Add ingestion step + storage (SQLite/Chroma) + lookup service.
  - Wire into meal analysis normalizers.
     Status: DONE (seed datasets defined + canonical ingestion loads full default set).

  3. Chat cannot log meals
     Problem: Chat agent does not expose a “log meal” action.
     Solve:

  - Add a tool/action to ChatAgent that maps to features/meals service.
  - Provide a structured schema for chat input → meal log request.
  - Confirm in chat UI with success/error response.
     Status: DONE (chat meal logging, confirmation flow, and follow-up responses implemented).

  4. UI redesign needed
     Problem: Current UI lacks visual hierarchy and polish.
     Solve:

  - Define a new visual system (type scale, layout grid, component tokens).
  - Refresh chat + dashboard + navigation components.
     Status: DONE (impeccable redesign applied across pages).

  5. Chat output should stream
     Problem: Output appears only after full response, not streamed.
     Solve:

  - Ensure chat endpoint uses SSE token events.
  - Frontend consumes event stream and renders incrementally.
  - Add “done/error” events for graceful termination.
     Status: DONE (SSE streaming with token/done/error in chat + audio).

  6. Markdown rendering in chat
     Problem: Output is plain text; Markdown not rendered.
     Solve:

  - Use a Markdown renderer in the chat UI.
  - Sanitize/whitelist allowed tags and handle code blocks.
     Status: DONE (ReactMarkdown + sanitize).

  7. Chat should load user health profiles + past meals
     Problem: Chat lacks personalized context from user health and meals.
     Solve:

  - Add CaseSnapshot/profile loader to ChatAgent inputs.
  - Inject recent meal logs and health profile in system context.
  - Apply size limits + summarization.
     Status: DONE (snapshot + health profile context injected).

  8. UI jitter/shaking during output
     Problem: Layout shifts during streaming.
     Solve:

  - Reserve vertical space for stream.
  - Use stable line-height and fixed container size.
  - Avoid rerender loops; debounced updates.
     Status: DONE (stream buffer + debounce + stable layout).

  9. Meal analysis logging is wrong
     Problem: Logs are inconsistent or mis‑tagged.
     Solve:

  - Audit logging calls in meal analysis pipeline.
  - Standardize structured fields (meal_id, user_id, provider, latency).
  - Add test or sample log validation.
     Status: DONE (provider/model/observation ids + inference latency standardized).

  10. Reminder delivery settings should be per‑account and should be moved into user settings in the UI
     Problem: Reminder delivery is currently global or not user‑scoped.
     Solve:

  - Add user settings model for reminders.
  - Wire settings into reminder scheduler + notification dispatch.
  - Add UI for settings.
     Status: DONE (per-account destinations respected for reminder outbox delivery).

  11. ChatAgent should know tools + cross‑tab context
     Problem: Chat doesn’t integrate with global tool registry or user actions
     outside chat.
     Solve:

  - Expose tool registry to chat via agent runtime.
  - Feed cross‑tab events into a shared context store.
  - Maintain strict safety gates.

  12. Refactor ChatAgent
     Problem: Chat agent structure is inconsistent and hard to evolve.
     Solve:

  - Define a single entrypoint, typed schemas, and structured event envelope.
  - Consolidate runtime logic and remove direct client usage.
     Status: IN PROGRESS (core refactor landed; follow-up consolidation still needed).

  13. Refactor memory services
     Problem: Memory stack is fragmented, not async‑safe.
     Solve:

  - Unify memory storage interface.
  - Add consistent async update behavior.
  - Enforce per‑user scoping and retention.
     Status: PARTIAL (Mem0-backed MemoryStore added; retention still pending).

  15. Mem0 chat memory layer
     Problem: Long-term personalization memories are not persisted.
     Solve:

  - Add Mem0 memory store adapter.
  - Fetch top-k snippets per user and inject into chat context.
  - Record chat turns back into Mem0.
     Status: DONE (Mem0 store + chat integration + tests).

  14. Refactor EmotionAgent workflow
     Problem: Emotion flow is disjoint (chat vs agent).
     Solve:

  - Centralize emotion inference in a single runtime.
  - Add clear enable/disable flags and degrade gracefully.
  - Align chat usage with emotion service contract.
     Status: IN PROGRESS (runtime unified; enable/disable flags pending UI/env polish).

## Architecture Critiques (Agreed)

1. Orchestration vs choreography
   Problem: Orchestrators must be edited to add new behaviors, creating tight coupling.
   Solve:
   - Introduce reaction subscribers that can respond to domain events without touching orchestrators.
   - Reserve orchestrators for safety-critical decisions only.
   Status: TODO

2. Transactional timeline writes
   Problem: Timeline emission is best-effort and can fail without rolling back business logic.
   Solve:
   - Make timeline writes part of the same transaction as the state change.
   - Or move timeline writes into an outbox-backed persistence path.
   Status: TODO

3. Snapshot bottleneck
   Problem: Rebuilding full snapshots on every interaction grows increasingly expensive.
   Solve:
   - Make projection sections the default read path.
   - Add pruning and per-agent context selection.
   Status: TODO

4. Duck-typed outbox repository methods
   Problem: `getattr`-based optional methods can silently disable lifecycle updates.
   Solve:
   - Replace with strict repository protocols.
   - Fail fast when lifecycle hooks are missing.
   Status: TODO

5. LLM latency stacking
   Problem: Emotion + LangGraph + service calls run on every request, even trivial ones.
   Solve:
   - Add a fast-path intent gate for simple messages.
   - Skip heavyweight agents unless required.
   Status: TODO

6. Double validation overhead
   Problem: Agents and services both validate the same payloads, increasing CPU cost.
   Solve:
   - Reuse shared Pydantic envelopes across agent/service boundaries.
   - Reduce duplicate validation for trusted internal flows.
   Status: TODO

## Additional Design Debt Candidates

1. Best-effort timeline append in orchestration flows (audit risk).
2. Snapshot rebuild still appears on hot request paths.
3. Optional outbox lifecycle methods via `getattr` in alert outbox.
4. Lack of fast-path for low-intent chat messages.
5. Redundant validation layers across agent/service boundaries.

## Message Channels Refactor Plan (OpenClaw-style)

Goal: Generalize reminder channels into message channels that support chat + media (Telegram/WhatsApp/etc) and migrate existing reminder preferences/endpoints in-place.

Status: IN PROGRESS

Plan:
1. Rename domain contracts and API schemas to Message*
2. Add attachment list schema to message payloads (type, url, mime, caption, size)
3. Migrate reminder channel tables/fields in-place to message equivalents
4. Update delivery pipeline to route by MessageChannel and include attachments
5. Add full‑duplex inbound ingestion (Telegram webhook + normalized payload)
6. Maintain backwards compatibility via adapters in reminder flows
7. Add migration tests + API contract tests

## Message Channels Initial Conversation (Outbound Welcome)

Status: IN PROGRESS

Plan:
1. Add message thread storage (message_threads + participants) and repositories
2. Send a welcome message when a message endpoint/channel is linked
3. Store the welcome in the message thread for future conversation context
4. Keep reminder delivery mapped to message channels until full migration is done
