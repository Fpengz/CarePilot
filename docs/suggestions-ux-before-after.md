# Suggestions UX Before/After

## Before
- Primary detail inspection relied on raw JSON view.
- Loading/empty/error states were implicit and inconsistent.
- Filter and scope controls lacked explicit state semantics.
- Error messages surfaced low-level API text.

## After
- Typed view models drive history and detail rendering.
- Explicit states for loading, empty, error, and partial data.
- Scope/filter controls use `aria-pressed` and disabled state during loads.
- Error semantics map API failures to actionable user messages.
- Raw JSON moved to optional debug disclosure.

## Files Updated
- `apps/web/app/suggestions/page.tsx`
- `apps/web/lib/suggestions-view-model.ts`
