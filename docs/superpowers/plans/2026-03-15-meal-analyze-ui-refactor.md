# Meal Analyze UI Refactor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the Meals UI to consume the current meal analysis API response shape and remove all reliance on the legacy `summary` object.

**Architecture:** Keep the backend contract unchanged and refactor the frontend to render directly from `validated_event`, `nutrition_profile`, and `raw_observation`. Use a small type-level contract check to make the API shape explicit and catch regressions during typecheck.

**Tech Stack:** Next.js (React), TypeScript, TanStack Query.

---

## Chunk 1: Types + Contract Guardrail

### Task 1: Add a Type-Level Contract Check and Update API Types

**Task Contract**  
**Goal:** Make the frontend meal analysis response type match the backend and enforce key presence via typecheck.  
**Scope:** Add a type-level guard and update `MealAnalyzeApiResponse` shape only.  
**Files:**  
- Create: `/Users/zhoufuwang/Projects/dietary_tools/apps/web/lib/contracts/meal-analyze-contract.ts`  
- Modify: `/Users/zhoufuwang/Projects/dietary_tools/apps/web/lib/types.ts`  
**Validation:** `pnpm web:typecheck` (fail then pass).  
**Risk:** Low; type-only changes may surface compile errors in dependent UI.  

**Files:**
- Create: `/Users/zhoufuwang/Projects/dietary_tools/apps/web/lib/contracts/meal-analyze-contract.ts`
- Modify: `/Users/zhoufuwang/Projects/dietary_tools/apps/web/lib/types.ts`
- Test: `pnpm web:typecheck`

- [ ] **Step 1: Write the failing type-level contract check**

```ts
// /Users/zhoufuwang/Projects/dietary_tools/apps/web/lib/contracts/meal-analyze-contract.ts
import type { MealAnalyzeApiResponse } from "@/lib/types";

type HasKey<T, K extends PropertyKey> = K extends keyof T ? true : false;

type _ExpectValidatedEvent = HasKey<MealAnalyzeApiResponse, "validated_event">;
type _ExpectNutritionProfile = HasKey<MealAnalyzeApiResponse, "nutrition_profile">;
type _ExpectRawObservation = HasKey<MealAnalyzeApiResponse, "raw_observation">;
type _ExpectWorkflow = HasKey<MealAnalyzeApiResponse, "workflow">;

const _assertValidatedEvent: _ExpectValidatedEvent = true;
const _assertNutritionProfile: _ExpectNutritionProfile = true;
const _assertRawObservation: _ExpectRawObservation = true;
const _assertWorkflow: _ExpectWorkflow = true;
```

- [ ] **Step 2: Run typecheck to verify it fails**

Run: `pnpm web:typecheck`
Expected: FAIL with TypeScript errors that one or more required keys (`validated_event`, `nutrition_profile`, `raw_observation`, `workflow`) are missing.

- [ ] **Step 3: Update `MealAnalyzeApiResponse` to match the backend**

```ts
// /Users/zhoufuwang/Projects/dietary_tools/apps/web/lib/types.ts
export interface MealAnalyzeApiResponse {
  raw_observation: Record<string, unknown>;
  validated_event: Record<string, unknown>;
  nutrition_profile: Record<string, unknown>;
  output_envelope: Record<string, unknown> | null;
  workflow: WorkflowExecutionResult;
}
```

- [ ] **Step 4: Run typecheck to verify it passes**

Run: `pnpm web:typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add /Users/zhoufuwang/Projects/dietary_tools/apps/web/lib/contracts/meal-analyze-contract.ts \
  /Users/zhoufuwang/Projects/dietary_tools/apps/web/lib/types.ts

git commit -m "web: align meal analyze response type"
```

## Chunk 2: UI Refactor

### Task 2: Render the Latest Analysis Card from the New Fields

**Task Contract**  
**Goal:** Replace legacy `summary` rendering with the new response fields while preserving empty-state behavior.  
**Scope:** Update only the “Latest Analysis” tab UI bindings and placeholders.  
**Files:**  
- Modify: `/Users/zhoufuwang/Projects/dietary_tools/apps/web/app/meals/page.tsx`  
**Validation:** `pnpm web:typecheck` and manual UI check.  
**Risk:** Moderate UI regression if placeholders or conditionals are incorrect.  

**Files:**
- Modify: `/Users/zhoufuwang/Projects/dietary_tools/apps/web/app/meals/page.tsx`
- Test: `pnpm web:typecheck`

- [ ] **Step 1: Write the failing UI mapping check**

```ts
// /Users/zhoufuwang/Projects/dietary_tools/apps/web/app/meals/page.tsx
// Keep the current legacy `summary` usage; after Task 1 updates types,
// this file should fail typecheck and guide the refactor.
const legacySummary = lastAnalysis?.summary;
```

- [ ] **Step 2: Run typecheck to verify it fails**

Run: `pnpm web:typecheck`
Expected: FAIL with errors about `summary` not existing on `MealAnalyzeApiResponse`.

- [ ] **Step 3: Update the “Latest Analysis” card bindings**

```tsx
// /Users/zhoufuwang/Projects/dietary_tools/apps/web/app/meals/page.tsx
const validated = lastAnalysis?.validated_event as Record<string, unknown> | undefined;
const nutrition = lastAnalysis?.nutrition_profile as Record<string, unknown> | undefined;
const observation = lastAnalysis?.raw_observation as Record<string, unknown> | undefined;

const mealName = typeof validated?.meal_name === "string" ? validated.meal_name : "Meal";
const capturedAt = typeof validated?.captured_at === "string" ? validated.captured_at : "—";
const caloriesText = typeof nutrition?.calories === "number" ? `${Math.round(nutrition.calories)} kcal` : "—";
const confidenceText =
  typeof observation?.confidence_score === "number" ? `${Math.round(observation.confidence_score * 100)}%` : "—";
```

And update the card fields to use `mealName`, `confidenceText`, `caloriesText`, and `capturedAt`, removing any `summary.*` usage. Keep the “Portion” metric card, but render `"—"` (or an explicit fallback) since no stable portion field exists in the new response. Add a new “Captured” metric card so the timestamp is visible without replacing Portion.

Also keep the empty-state conditional by checking `lastAnalysis == null` (missing fields should show “—” rather than hiding the UI). Keep the “Raw Response” JSON viewer unchanged.

- [ ] **Step 4: Run typecheck to verify it passes**

Run: `pnpm web:typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add /Users/zhoufuwang/Projects/dietary_tools/apps/web/app/meals/page.tsx

git commit -m "web: render latest meal analysis from v2 response"
```

---

**Manual Validation**
- Analyze a meal in the UI and confirm the “Latest Analysis” tab shows meal name, calories, confidence %, and timestamp.
- Confirm the “Raw Response” JSON viewer still renders.
