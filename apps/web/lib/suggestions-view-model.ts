import type { SuggestionItemApi } from "@/lib/types";

export type SuggestionScope = "self" | "household";
export type SuggestionsLoadState = "idle" | "loading" | "ready" | "error";

export interface SuggestionSummaryViewModel {
  id: string;
  createdAtLabel: string;
  sourceUserId: string;
  sourceDisplayName: string;
  safetyDecision: SuggestionItemApi["safety"]["decision"];
  safe: boolean;
}

export interface SuggestionDetailViewModel {
  item: SuggestionItemApi;
  hasReadings: boolean;
  hasRiskFlags: boolean;
  hasWorkflowEvents: boolean;
  hasRecommendationAdvice: boolean;
  isPartial: boolean;
  partialReasons: string[];
}

export function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function buildSuggestionSummaries(items: SuggestionItemApi[]): SuggestionSummaryViewModel[] {
  return items.map((item) => ({
    id: item.suggestion_id,
    createdAtLabel: formatDate(item.created_at),
    sourceUserId: item.source_user_id,
    sourceDisplayName: item.source_display_name,
    safetyDecision: item.safety.decision,
    safe: Boolean(item.recommendation?.safe),
  }));
}

export function buildSuggestionDetail(item: SuggestionItemApi | null): SuggestionDetailViewModel | null {
  if (!item) return null;
  const hasReadings = item.report_parse.readings.length > 0;
  const hasRiskFlags = item.report_parse.snapshot.risk_flags.length > 0;
  const hasWorkflowEvents = Array.isArray(item.workflow.timeline_events) && item.workflow.timeline_events.length > 0;
  const recommendation = item.recommendation as Record<string, unknown>;
  const advice = recommendation.localized_advice;
  const hasRecommendationAdvice =
    Array.isArray(advice) && advice.every((entry) => typeof entry === "string") && advice.length > 0;

  const partialReasons: string[] = [];
  if (!hasReadings) partialReasons.push("No parsed readings were extracted from the report.");
  if (!hasWorkflowEvents) partialReasons.push("Workflow trace events are unavailable for this suggestion.");
  if (!hasRecommendationAdvice) partialReasons.push("Recommendation advice is missing or incomplete.");

  return {
    item,
    hasReadings,
    hasRiskFlags,
    hasWorkflowEvents,
    hasRecommendationAdvice,
    isPartial: partialReasons.length > 0,
    partialReasons,
  };
}

export function toSuggestionErrorMessage(error: unknown): string {
  const raw = error instanceof Error ? error.message : String(error);
  if (raw.includes("API 400")) return "The request was accepted but report context is incomplete. Add a meal record and try again.";
  if (raw.includes("API 401")) return "Your session has expired. Sign in again to continue.";
  if (raw.includes("API 403")) return "You do not have permission for this suggestion scope.";
  if (raw.includes("API 404")) return "The suggestion could not be found in the current visibility scope.";
  if (raw.includes("API 409")) return "The request conflicts with current state. Refresh and retry.";
  return "We could not complete the suggestions request. Retry or adjust your scope/filter.";
}
