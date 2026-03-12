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
