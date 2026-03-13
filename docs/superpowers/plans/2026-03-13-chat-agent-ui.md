# Chat Agent UI Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Chat Agent page with a clinical, warm, and information-rich layout while preserving existing chat streaming, audio recording, and meal proposal flows.

**Architecture:** Add dedicated chat UI components (rail, message card, input dock) and a message kind mapper in the page. Keep all existing network flows and event handling in `page.tsx`, only reshaping presentation and deriving structured message metadata on the client.

**Tech Stack:** Next.js App Router, React, Tailwind CSS, `react-markdown`, `rehype-sanitize`, `next/font/google`.

---

## File Structure

- Create/Modify: `apps/web/app/chat/components/types.ts` — message types, view models.
- Create/Modify: `apps/web/app/chat/components/message-card.tsx` — structured assistant/user card rendering.
- Create/Modify: `apps/web/app/chat/components/chat-rail.tsx` — signal rail (emotion, last intent, focus).
- Create: `apps/web/app/chat/components/chat-input.tsx` — chips + input + send + mic trigger.
- Modify: `apps/web/app/chat/page.tsx` — layout composition, message mapping, font setup, wiring to existing handlers.

---

## Chunk 1: Component Foundations

### Task 1: Define chat message types and view model

**Files:**
- Modify/Create: `apps/web/app/chat/components/types.ts`

- [ ] **Step 1: Confirm UI test harness availability**

Run: `rg -n "vitest|jest|testing-library" apps/web -S`
Expected: No matches. If tests are found, add a minimal render test for `MessageCard` and update the plan accordingly.

- [ ] **Step 2: Write minimal types**

```ts
export type MessageKind =
  | "plain"
  | "proactive_alert"
  | "meal_analysis"
  | "recommendation"
  | "follow_up"
  | "trend_insight";

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  tag?: string;
  emotion?: { label: string; score: number; productState?: string | null };
  mealProposal?: { proposalId: string; mealText: string };
};

export type MessageView = Message & {
  kind: MessageKind;
  title?: string;
  explanation?: string;
  reasoning?: string;
  confidence?: number;
};
```

- [ ] **Step 3: Typecheck**

Run: `pnpm web:typecheck`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add apps/web/app/chat/components/types.ts
# commit once other component tasks are ready
```

### Task 2: Implement MessageCard component

**Files:**
- Modify/Create: `apps/web/app/chat/components/message-card.tsx`

- [ ] **Step 1: Add component shell**

```tsx
export function MessageCard({ message, isStreaming, streamDraft, onMealAction, proposalLoadingId }: Props) {
  // render title, badge, content, confidence, reasoning, and actions
}
```

- [ ] **Step 2: Add structured slots**
- title + badge row
- explanation text
- markdown body using `react-markdown` + `rehype-sanitize`
- confidence meter (progress bar) with `ConfidenceMeter` subcomponent
- reasoning disclosure block
- meal proposal buttons

- [ ] **Step 3: Add internal subcomponents**

```tsx
function MessageKindBadge({ kind }: { kind: MessageKind }) {
  // map kind -> label + color
}

function ConfidenceMeter({ value }: { value?: number }) {
  // render progress bar + percentage
}
```

- [ ] **Step 4: Typecheck**

Run: `pnpm web:typecheck`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/web/app/chat/components/message-card.tsx
# commit once other component tasks are ready
```

### Task 3: Implement ChatRail component

**Files:**
- Modify/Create: `apps/web/app/chat/components/chat-rail.tsx`

- [ ] **Step 1: Add rail layout**

```tsx
export function ChatRail({ lastEmotion, lastUserMessage }: Props) {
  // render signal summary + next check-in + focus cue
}
```

- [ ] **Step 2: Style for calm clinical tone**

- [ ] **Step 3: Typecheck**

Run: `pnpm web:typecheck`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add apps/web/app/chat/components/chat-rail.tsx
# commit once other component tasks are ready
```

### Task 4: Implement ChatInput component

**Files:**
- Create: `apps/web/app/chat/components/chat-input.tsx`

- [ ] **Step 1: Add input dock structure**

```tsx
export function ChatInput({ input, onInputChange, onSend, onRecord, loading, ... }: Props) {
  // chips + textarea + send + mic
}
```

- [ ] **Step 2: Wire suggestion chips**
- Include 4-5 example prompts
- Keep [TRACK] prefix button

- [ ] **Step 3: Accessibility pass**
- Ensure chip buttons are keyboard focusable
- Add `aria-label` for mic, send, and menu buttons
- Preserve visible focus rings

- [ ] **Step 4: Typecheck**

Run: `pnpm web:typecheck`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/web/app/chat/components/chat-input.tsx
# commit once other component tasks are ready
```

---

## Chunk 2: Page Integration and Validation

### Task 5: Refactor Chat page layout and wiring

**Files:**
- Modify: `apps/web/app/chat/page.tsx`

- [ ] **Step 1: Add font pairing**

```ts
import { Fraunces, Source_Sans_3 } from "next/font/google";
```

Apply fonts at container level via className or inline style to avoid global overrides.

- [ ] **Step 2: Add message kind mapper**

```ts
function deriveMessageView(message: Message): MessageView {
  // map tags/content heuristics to MessageKind and optional title/explanation
}
```

Heuristics (precedence order):
1. `message.tag === "error"` or content starts with "⚠" -> `proactive_alert`
2. `message.mealProposal` or content includes "meal analysis", "macros", "calories" -> `meal_analysis`
3. content includes "trend", "over time", "week", "pattern" -> `trend_insight`
4. content includes "recommend", "suggest", "consider" -> `recommendation`
5. content includes "clarify", "follow up", or ends with "?" -> `follow_up`
6. default -> `plain`

Set `confidence` and `reasoning` only when available from known cues; otherwise leave undefined and hide the sections.

- [ ] **Step 3: Replace inline message rendering**

Use `MessageCard` for assistant/user messages. Ensure streaming state uses `streamDraft` for the last assistant message.

- [ ] **Step 4: Compose layout**
- Left rail: `ChatRail`
- Main: conversation list + empty state
- Bottom: `ChatInput`
- Add inline non-blocking notices for stream interruption and audio errors
- Ensure readable line lengths (max width for long text)

- [ ] **Step 5: Preserve handlers**
Keep `handleSend`, audio recording, meal proposal confirm intact. Only rewire to new component props.

- [ ] **Step 6: Accessibility pass**
- Ensure keyboard navigation order remains logical
- Add ARIA labels for interactive icons
- Keep focus indicators visible

- [ ] **Step 7: Keep emotion mapping unchanged**
Preserve existing emotion fields (`label`, `score`) without adding new properties.

- [ ] **Step 8: Typecheck**

Run: `pnpm web:typecheck`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add apps/web/app/chat/page.tsx
# include component files from Chunk 1 in this commit if not yet committed
```

### Task 6: Final validation and visual smoke

**Files:**
- None

- [ ] **Step 1: Lint + build**

Run:
- `pnpm web:lint`
- `pnpm web:typecheck`
- `pnpm web:build`

Expected: all PASS

- [ ] **Step 2: Visual smoke**

Run: `uv run python scripts/dg.py dev --no-api` and open `http://localhost:3000/chat` to confirm layout, streaming, and input dock rendering.

- [ ] **Step 3: Commit final polish**

```bash
git add apps/web/app/chat/page.tsx apps/web/app/chat/components/*.tsx
# include any minor tweaks
```

---

## Chunk 3: Quality Passes (Impeccable Skills)

**Task Contract**
- **Goal:** Ensure the redesigned chat page meets high-quality UX standards through audit, distill, and polish passes.
- **Scope:** UI-only adjustments for chat layout and components; no backend or API changes.
- **Files:** `apps/web/app/chat/page.tsx`, `apps/web/app/chat/components/*.tsx`, `reports/chat-agent-ui-audit.md`.
- **Validation:** `pnpm web:lint`, `pnpm web:typecheck`, `pnpm web:build`.
- **Risk:** Over-simplification that removes helpful guidance or weakens clarity; mitigate by preserving all core behaviors and validating with audit findings.

### Task 7: Audit the updated chat page

**Files:**
- Create: `reports/chat-agent-ui-audit.md`

- [ ] **Step 1: Run audit pass**

Run the `/audit` skill against route `/chat` (entry: `apps/web/app/chat/page.tsx`) and save the report to `reports/chat-agent-ui-audit.md` with severity tags and file references.
Expected: report includes severity tags + file references per finding.

- [ ] **Step 2: Capture fixes to apply**

Summarize the specific changes needed before polishing in `reports/chat-agent-ui-audit.md` under a “Fix Plan” section with per-file action items.

- [ ] **Step 3: Apply audit Fix Plan changes**
- Implement the per-file updates from the “Fix Plan” section.
- Run: `pnpm web:lint`
- Run: `pnpm web:typecheck`
Expected: PASS

### Task 8: Distill the interface

**Files:**
- Modify: `apps/web/app/chat/page.tsx`
- Modify: `apps/web/app/chat/components/*.tsx`

- [ ] **Step 1: Run `/distill` skill pass**
Target route `/chat` (entry: `apps/web/app/chat/page.tsx`).
Expected: no layout regression; all core controls remain.

- [ ] **Step 2: Identify non-essential UI**
- Remove redundancy and unnecessary containers without removing features.
- Criteria: eliminate repeated headings, nested panels, or redundant helper copy; keep one primary action, preserve meal proposal controls and audio recording.

- [ ] **Step 3: Implement simplifications**
- Target outcomes:
- Remove redundant headers or helper copy that repeat the title/eyebrow.
- Reduce nested containers in the message list and input dock by one level where possible.
- Ensure no new UI blocks are added beyond rail, stream, and input dock.

- [ ] **Step 4: Typecheck**

Run: `pnpm web:typecheck`
Expected: PASS

### Task 9: Polish the final UI

**Files:**
- Modify: `apps/web/app/chat/page.tsx`
- Modify: `apps/web/app/chat/components/*.tsx`

- [ ] **Step 1: Run `/polish` skill pass**
Target route `/chat` (entry: `apps/web/app/chat/page.tsx`).
Expected: no layout regression; all core controls remain.

- [ ] **Step 2: Visual/typography alignment pass**
- Verify `MessageCard` title/body hierarchy and line lengths (45–75 chars).
- Ensure `ChatRail` spacing aligns with main column and uses consistent typographic scale.

- [ ] **Step 3: Interaction states and focus**
- Check hover/focus/disabled states for chips, send button, mic/menu button, and meal proposal actions.
- Ensure focus rings are visible and contrast meets WCAG AA.

- [ ] **Step 4: Final validation**

Run:
- `pnpm web:lint`
- `pnpm web:typecheck`
- `pnpm web:build`

Expected: all PASS
