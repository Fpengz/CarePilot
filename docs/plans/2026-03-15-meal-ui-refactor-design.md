# Meal UI Refactor to New Analyze Response (Design)

## Goal
Update the Meals UI to consume the current meal analysis API response shape (`validated_event`, `nutrition_profile`, `raw_observation`, `workflow`) and remove reliance on the legacy `summary` object.

## Scope
- Frontend-only change.
- Update types to match the backend response.
- Refactor the “Latest Analysis” tab to render from the new fields.
- Preserve existing empty/placeholder behavior.

## Non-Goals
- No backend contract changes.
- No changes to meal upload workflow or persistence.
- No redesign of meal history or summary cards beyond field bindings.

## Approach
- Replace `MealAnalyzeApiResponse.summary` usage with direct access to:
  - `validated_event.meal_name`
  - `validated_event.captured_at`
  - `validated_event.needs_manual_review`
  - `nutrition_profile.calories` (and optionally other totals)
  - `raw_observation.confidence_score` (or `validated_event.confidence_summary` if needed)
- Keep the raw JSON viewer unchanged.
- Keep null/undefined fields as “—” in UI.

## Data Mapping
- Meal: `validated_event.meal_name`
- Confidence: `raw_observation.confidence_score` (0–1) → percent
- Calories: `nutrition_profile.calories`
- Portion: show “—” unless a stable portion field is added in the new model
- Timestamp: `validated_event.captured_at`

## Error/Empty Handling
- If `lastAnalysis` is null, continue to show the empty-state message.
- If `nutrition_profile` or `raw_observation` fields are missing, show “—”.

## Validation
- Manual: analyze a meal; confirm “Latest Analysis” shows meal name, calories, confidence, and timestamp; raw JSON still renders.

## Risks
- Slight UI regression if new response fields are missing or renamed in backend.
- Confidence score semantics may differ from legacy `summary.confidence`.
