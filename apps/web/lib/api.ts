import type {
  AlertTimelineApiResponse,
  AlertTriggerApiResponse,
  RecommendationAgentApiResponse,
  RecommendationInteractionApiResponse,
  RecommendationInteractionEventType,
  RecommendationSubstitutionApiResponse,
  AuthAuditEventListResponse,
  HouseholdActiveUpdateResponse,
  HouseholdBundleApiResponse,
  HouseholdCareMealSummaryResponse,
  HouseholdCareMembersResponse,
  HouseholdCareProfileResponse,
  HouseholdCareReminderListResponse,
  HouseholdInviteCreateResponse,
  HouseholdLeaveResponse,
  HouseholdMemberRemoveResponse,
  HouseholdMembersResponse,
  AuthLoginResponse,
  AuthPasswordUpdateResponse,
  AuthProfileUpdateResponse,
  AuthSessionListResponse,
  AuthSessionRevokeOthersResponse,
  AuthSessionRevokeResponse,
  DailySuggestionsResponse,
  HealthProfileResponse,
  HealthProfileOnboardingResponse,
  MealAnalyzeApiResponse,
  MealDailySummaryApiResponse,
  MealRecordsApiResponse,
  MealWeeklySummaryApiResponse,
  MedicationAdherenceMetricsApiResponse,
  MedicationRegimenEnvelopeApiResponse,
  MedicationRegimenListApiResponse,
  MetricTrendListApiResponse,
  MobilityReminderSettingsEnvelopeResponse,
  RecommendationGenerateApiResponse,
  ClinicalCardEnvelopeApiResponse,
  ClinicalCardListApiResponse,
  SymptomCheckInEnvelopeApiResponse,
  SymptomCheckInListApiResponse,
  SymptomSummaryApiResponse,
  ToolPolicyConditionsApi,
  ToolPolicyEvaluationApiResponse,
  ToolPolicyListApiResponse,
  ToolPolicyWriteApiResponse,
  SuggestionDetailApiResponse,
  SuggestionGenerateApiResponse,
  SuggestionListApiResponse,
  ReminderConfirmApiResponse,
  ReminderNotificationEndpointListResponse,
  ReminderNotificationLogListResponse,
  ReminderNotificationPreferenceListResponse,
  ReminderGenerateApiResponse,
  ReminderListApiResponse,
  ScheduledReminderNotificationListResponse,
  ReportParseApiResponse,
  SessionUser,
  WorkflowExecutionResult,
  WorkflowListApiResponse,
  WorkflowRuntimeRegistryApiResponse,
  WorkflowSnapshotCompareApiResponse,
  WorkflowSnapshotListApiResponse,
  WorkflowSnapshotWriteApiResponse,
  ApiErrorEnvelope,
} from "@/lib/types";
import { getConsolePrinter } from "@/lib/console-safe";

// Legacy consolidated client kept for compatibility. Prefer domain clients under `@/lib/api/*`.
// Planned removal: v0.2.0 (follow-up migration PR).

// Default to same-origin proxy so browser auth cookies stay first-party for localhost and LAN hosts.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/backend";
const FRONTEND_API_LOG_ENABLED = process.env.NEXT_PUBLIC_DEV_LOG_FRONTEND === "1" || process.env.NEXT_PUBLIC_DEV_LOG_FRONTEND === "true";
const FRONTEND_API_LOG_VERBOSE = process.env.NEXT_PUBLIC_DEV_LOG_FRONTEND_VERBOSE === "1" || process.env.NEXT_PUBLIC_DEV_LOG_FRONTEND_VERBOSE === "true";

function redactSensitive<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((item) => redactSensitive(item)) as T;
  }
  if (value && typeof value === "object") {
    const source = value as Record<string, unknown>;
    const redacted: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(source)) {
      const lower = key.toLowerCase();
      if (
        lower.includes("password") ||
        lower.includes("token") ||
        lower.includes("secret") ||
        lower.includes("cookie")
      ) {
        redacted[key] = "***";
      } else {
        redacted[key] = redactSensitive(val);
      }
    }
    return redacted as T;
  }
  return value;
}

function parseJsonMaybe(body: string): unknown {
  try {
    return JSON.parse(body) as unknown;
  } catch {
    return body;
  }
}

function logFrontendApi(event: string, payload: Record<string, unknown>) {
  if (!FRONTEND_API_LOG_ENABLED || typeof window === "undefined") return;
  const printer = getConsolePrinter(console, event);
  printer(`[frontend-api] ${event}`, redactSensitive(payload));
}

function isApiErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  if (!value || typeof value !== "object") return false;
  const payload = value as Record<string, unknown>;
  const error = payload.error;
  return (
    typeof payload.detail === "string" &&
    !!error &&
    typeof error === "object" &&
    typeof (error as Record<string, unknown>).code === "string" &&
    typeof (error as Record<string, unknown>).message === "string"
  );
}

export class ApiRequestError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly error: ApiErrorEnvelope["error"];
  readonly envelope: ApiErrorEnvelope;
  readonly requestId: string | null;
  readonly correlationId: string | null;

  constructor(args: {
    status: number;
    detail: string;
    envelope: ApiErrorEnvelope;
    requestId: string | null;
    correlationId: string | null;
  }) {
    super(`API ${args.status}: ${args.detail}`);
    this.name = "ApiRequestError";
    this.status = args.status;
    this.detail = args.detail;
    this.error = args.envelope.error;
    this.envelope = args.envelope;
    this.requestId = args.requestId;
    this.correlationId = args.correlationId;
  }
}

export function isApiRequestError(error: unknown): error is ApiRequestError {
  return error instanceof ApiRequestError;
}

function buildApiRequestError(response: Response, rawBody: string): ApiRequestError {
  const parsed = parseJsonMaybe(rawBody);
  const envelope = isApiErrorEnvelope(parsed)
    ? parsed
    : {
        detail: typeof parsed === "string" && parsed.trim() ? parsed : response.statusText || "request failed",
        error: {
          code: "request.error",
          message: typeof parsed === "string" && parsed.trim() ? parsed : response.statusText || "request failed",
          details: {},
          correlation_id: response.headers.get("x-correlation-id"),
          status_code: response.status,
        },
      };
  return new ApiRequestError({
    status: response.status,
    detail: envelope.detail,
    envelope,
    requestId: response.headers.get("x-request-id"),
    correlationId: response.headers.get("x-correlation-id") ?? envelope.error.correlation_id ?? null,
  });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method ?? "GET";
  const startedAt = performance.now();
  const bodyPreview =
    FRONTEND_API_LOG_VERBOSE && typeof init?.body === "string" ? redactSensitive(parseJsonMaybe(init.body)) : undefined;
  logFrontendApi("request.start", { method, path, body: bodyPreview });

  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    const error = buildApiRequestError(response, text);
    logFrontendApi("request.error", {
      method,
      path,
      status: response.status,
      duration_ms: Math.round((performance.now() - startedAt) * 100) / 100,
      response: FRONTEND_API_LOG_VERBOSE ? redactSensitive(parseJsonMaybe(text)) : text.slice(0, 200),
      request_id: error.requestId,
      correlation_id: error.correlationId,
      error_code: error.error.code,
    });
    throw error;
  }
  const json = (await response.json()) as T;
  logFrontendApi("request.success", {
    method,
    path,
    status: response.status,
    duration_ms: Math.round((performance.now() - startedAt) * 100) / 100,
    request_id: response.headers.get("x-request-id"),
    correlation_id: response.headers.get("x-correlation-id"),
    response: FRONTEND_API_LOG_VERBOSE ? json : undefined,
  });
  return json;
}

export async function login(email: string, password: string): Promise<AuthLoginResponse> {
  return request<AuthLoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function signup(payload: {
  email: string;
  password: string;
  display_name?: string;
  profile_mode?: "self" | "caregiver";
}): Promise<AuthLoginResponse> {
  return request<AuthLoginResponse>("/api/v1/auth/signup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function logout(): Promise<void> {
  await request("/api/v1/auth/logout", { method: "POST" });
}

export async function me(): Promise<{ user: SessionUser }> {
  return request<{ user: SessionUser }>("/api/v1/auth/me");
}

export async function updateAuthProfile(payload: {
  display_name?: string;
  profile_mode?: "self" | "caregiver";
}): Promise<AuthProfileUpdateResponse> {
  return request<AuthProfileUpdateResponse>("/api/v1/auth/profile", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getHealthProfile(): Promise<HealthProfileResponse> {
  return request<HealthProfileResponse>("/api/v1/profile/health");
}

export async function getHealthProfileOnboarding(): Promise<HealthProfileOnboardingResponse> {
  return request<HealthProfileOnboardingResponse>("/api/v1/profile/health/onboarding");
}

export async function updateHealthProfileOnboarding(payload: {
  step_id: string;
  profile?: {
    age?: number | null;
    locale?: string;
    height_cm?: number | null;
    weight_kg?: number | null;
    daily_sodium_limit_mg?: number;
    daily_sugar_limit_g?: number;
    daily_protein_target_g?: number;
    daily_fiber_target_g?: number;
    target_calories_per_day?: number | null;
    macro_focus?: string[];
    conditions?: Array<{ name: string; severity: string }>;
    medications?: Array<{ name: string; dosage: string; contraindications: string[] }>;
    allergies?: string[];
    nutrition_goals?: string[];
    preferred_cuisines?: string[];
    disliked_ingredients?: string[];
    budget_tier?: "budget" | "moderate" | "flexible";
  };
}): Promise<HealthProfileOnboardingResponse> {
  return request<HealthProfileOnboardingResponse>("/api/v1/profile/health/onboarding", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function completeHealthProfileOnboarding(): Promise<HealthProfileOnboardingResponse> {
  return request<HealthProfileOnboardingResponse>("/api/v1/profile/health/onboarding/complete", {
    method: "POST",
  });
}

export async function updateHealthProfile(payload: {
  age?: number | null;
  locale?: string;
  height_cm?: number | null;
  weight_kg?: number | null;
  daily_sodium_limit_mg?: number;
  daily_sugar_limit_g?: number;
  daily_protein_target_g?: number;
  daily_fiber_target_g?: number;
  target_calories_per_day?: number | null;
  macro_focus?: string[];
  conditions?: Array<{ name: string; severity: string }>;
  medications?: Array<{ name: string; dosage: string; contraindications: string[] }>;
  allergies?: string[];
  nutrition_goals?: string[];
  preferred_cuisines?: string[];
  disliked_ingredients?: string[];
  budget_tier?: "budget" | "moderate" | "flexible";
}): Promise<HealthProfileResponse> {
  return request<HealthProfileResponse>("/api/v1/profile/health", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getDailySuggestions(): Promise<DailySuggestionsResponse> {
  return request<DailySuggestionsResponse>("/api/v1/suggestions/daily");
}

export async function getDailyAgentRecommendations(): Promise<RecommendationAgentApiResponse> {
  return request<RecommendationAgentApiResponse>("/api/v1/recommendations/daily-agent");
}

export async function getMealSubstitutions(payload: {
  source_meal_id?: string;
  limit?: number;
}): Promise<RecommendationSubstitutionApiResponse> {
  return request<RecommendationSubstitutionApiResponse>("/api/v1/recommendations/substitutions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function recordRecommendationInteraction(payload: {
  recommendation_id: string;
  candidate_id: string;
  event_type: RecommendationInteractionEventType;
  slot: "breakfast" | "lunch" | "dinner" | "snack";
  source_meal_id?: string;
  selected_meal_id?: string;
  metadata?: Record<string, unknown>;
}): Promise<RecommendationInteractionApiResponse> {
  return request<RecommendationInteractionApiResponse>("/api/v1/recommendations/interactions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateAuthPassword(payload: {
  current_password: string;
  new_password: string;
}): Promise<AuthPasswordUpdateResponse> {
  return request<AuthPasswordUpdateResponse>("/api/v1/auth/password", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function listAuthSessions(): Promise<AuthSessionListResponse> {
  return request<AuthSessionListResponse>("/api/v1/auth/sessions");
}

export async function revokeAuthSession(sessionId: string): Promise<AuthSessionRevokeResponse> {
  return request<AuthSessionRevokeResponse>(`/api/v1/auth/sessions/${sessionId}/revoke`, {
    method: "POST",
  });
}

export async function revokeOtherAuthSessions(): Promise<AuthSessionRevokeOthersResponse> {
  return request<AuthSessionRevokeOthersResponse>("/api/v1/auth/sessions/revoke-others", {
    method: "POST",
  });
}

export async function listAuthAuditEvents(limit = 20): Promise<AuthAuditEventListResponse> {
  return request<AuthAuditEventListResponse>(`/api/v1/auth/audit-events?limit=${limit}`);
}

export async function getCurrentHousehold(): Promise<HouseholdBundleApiResponse> {
  return request<HouseholdBundleApiResponse>("/api/v1/households/current");
}

export async function createHousehold(name: string): Promise<HouseholdBundleApiResponse> {
  return request<HouseholdBundleApiResponse>("/api/v1/households", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function renameHousehold(householdId: string, name: string): Promise<HouseholdBundleApiResponse> {
  return request<HouseholdBundleApiResponse>(`/api/v1/households/${householdId}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export async function listHouseholdMembers(householdId: string): Promise<HouseholdMembersResponse> {
  return request<HouseholdMembersResponse>(`/api/v1/households/${householdId}/members`);
}

export async function listHouseholdCareMembers(householdId: string): Promise<HouseholdCareMembersResponse> {
  return request<HouseholdCareMembersResponse>(`/api/v1/households/${householdId}/care/members`);
}

export async function getHouseholdCareMemberProfile(
  householdId: string,
  memberUserId: string,
): Promise<HouseholdCareProfileResponse> {
  return request<HouseholdCareProfileResponse>(
    `/api/v1/households/${householdId}/care/members/${memberUserId}/profile`,
  );
}

export async function getHouseholdCareMemberDailySummary(
  householdId: string,
  memberUserId: string,
  summaryDate: string,
): Promise<HouseholdCareMealSummaryResponse> {
  return request<HouseholdCareMealSummaryResponse>(
    `/api/v1/households/${householdId}/care/members/${memberUserId}/meal-daily-summary?date=${summaryDate}`,
  );
}

export async function listHouseholdCareMemberReminders(
  householdId: string,
  memberUserId: string,
): Promise<HouseholdCareReminderListResponse> {
  return request<HouseholdCareReminderListResponse>(
    `/api/v1/households/${householdId}/care/members/${memberUserId}/reminders`,
  );
}

export async function createHouseholdInvite(householdId: string): Promise<HouseholdInviteCreateResponse> {
  return request<HouseholdInviteCreateResponse>(`/api/v1/households/${householdId}/invites`, {
    method: "POST",
  });
}

export async function joinHousehold(code: string): Promise<HouseholdBundleApiResponse> {
  return request<HouseholdBundleApiResponse>("/api/v1/households/join", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export async function removeHouseholdMember(
  householdId: string,
  userId: string,
): Promise<HouseholdMemberRemoveResponse> {
  return request<HouseholdMemberRemoveResponse>(`/api/v1/households/${householdId}/members/${userId}/remove`, {
    method: "POST",
  });
}

export async function leaveHousehold(householdId: string): Promise<HouseholdLeaveResponse> {
  return request<HouseholdLeaveResponse>(`/api/v1/households/${householdId}/leave`, {
    method: "POST",
  });
}

export async function setActiveHousehold(householdId: string | null): Promise<HouseholdActiveUpdateResponse> {
  return request<HouseholdActiveUpdateResponse>("/api/v1/households/active", {
    method: "PATCH",
    body: JSON.stringify({ household_id: householdId }),
  });
}

export async function triggerAlert(payload: {
  alert_type: string;
  severity: "info" | "warning" | "critical";
  message: string;
  destinations: string[];
}): Promise<AlertTriggerApiResponse> {
  return request<AlertTriggerApiResponse>("/api/v1/alerts/trigger", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAlertTimeline(alertId: string): Promise<AlertTimelineApiResponse> {
  return request<AlertTimelineApiResponse>(`/api/v1/alerts/${alertId}/timeline`);
}

export async function listWorkflows(): Promise<WorkflowListApiResponse> {
  return request<WorkflowListApiResponse>("/api/v1/workflows");
}

export async function getWorkflow(correlationId: string): Promise<WorkflowExecutionResult> {
  return request<WorkflowExecutionResult>(`/api/v1/workflows/${correlationId}`);
}

export async function getWorkflowRuntimeContract(): Promise<WorkflowRuntimeRegistryApiResponse> {
  return request<WorkflowRuntimeRegistryApiResponse>("/api/v1/workflows/runtime-contract");
}

export async function listWorkflowContractSnapshots(): Promise<WorkflowSnapshotListApiResponse> {
  return request<WorkflowSnapshotListApiResponse>("/api/v1/workflows/runtime-contract/snapshots");
}

export async function createWorkflowContractSnapshot(): Promise<WorkflowSnapshotWriteApiResponse> {
  return request<WorkflowSnapshotWriteApiResponse>("/api/v1/workflows/runtime-contract/snapshots", {
    method: "POST",
  });
}

export async function compareWorkflowContractSnapshots(
  baseVersion: number,
  targetVersion: number,
): Promise<WorkflowSnapshotCompareApiResponse> {
  const query = new URLSearchParams({
    base_version: String(baseVersion),
    target_version: String(targetVersion),
  }).toString();
  return request<WorkflowSnapshotCompareApiResponse>(`/api/v1/workflows/runtime-contract/snapshots/compare?${query}`);
}

export async function listWorkflowToolPolicies(): Promise<ToolPolicyListApiResponse> {
  return request<ToolPolicyListApiResponse>("/api/v1/workflows/tool-policies");
}

export async function createWorkflowToolPolicy(payload: {
  role: "member" | "admin";
  agent_id: string;
  tool_name: string;
  effect: "allow" | "deny";
  conditions?: ToolPolicyConditionsApi;
  priority?: number;
  enabled?: boolean;
}): Promise<ToolPolicyWriteApiResponse> {
  return request<ToolPolicyWriteApiResponse>("/api/v1/workflows/tool-policies", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function patchWorkflowToolPolicy(
  policyId: string,
  payload: {
    effect?: "allow" | "deny";
    conditions?: ToolPolicyConditionsApi;
    priority?: number;
    enabled?: boolean;
  },
): Promise<ToolPolicyWriteApiResponse> {
  return request<ToolPolicyWriteApiResponse>(`/api/v1/workflows/tool-policies/${policyId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function evaluateWorkflowToolPolicy(params: {
  role: "member" | "admin";
  agent_id: string;
  tool_name: string;
  environment?: string;
}): Promise<ToolPolicyEvaluationApiResponse> {
  const query = new URLSearchParams({
    role: params.role,
    agent_id: params.agent_id,
    tool_name: params.tool_name,
    environment: params.environment ?? "dev",
  }).toString();
  return request<ToolPolicyEvaluationApiResponse>(`/api/v1/workflows/tool-policies/evaluation?${query}`);
}

export async function analyzeMeal(formData: FormData): Promise<MealAnalyzeApiResponse> {
  const startedAt = performance.now();
  logFrontendApi("request.start", {
    method: "POST",
    path: "/api/v1/meal/analyze",
    provider: formData.get("provider"),
    form_keys: FRONTEND_API_LOG_VERBOSE ? [...formData.keys()] : undefined,
  });
  const response = await fetch(`${API_BASE_URL}/api/v1/meal/analyze`, {
    method: "POST",
    body: formData,
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    const error = buildApiRequestError(response, text);
    logFrontendApi("request.error", {
      method: "POST",
      path: "/api/v1/meal/analyze",
      status: response.status,
      duration_ms: Math.round((performance.now() - startedAt) * 100) / 100,
      response: FRONTEND_API_LOG_VERBOSE ? redactSensitive(parseJsonMaybe(text)) : text.slice(0, 200),
      request_id: error.requestId,
      correlation_id: error.correlationId,
      error_code: error.error.code,
    });
    throw error;
  }
  const json = (await response.json()) as MealAnalyzeApiResponse;
  logFrontendApi("request.success", {
    method: "POST",
    path: "/api/v1/meal/analyze",
    status: response.status,
    duration_ms: Math.round((performance.now() - startedAt) * 100) / 100,
    request_id: response.headers.get("x-request-id"),
    correlation_id: response.headers.get("x-correlation-id"),
    response: FRONTEND_API_LOG_VERBOSE ? json : undefined,
  });
  return json;
}

export async function listMealRecords(limit?: number): Promise<MealRecordsApiResponse> {
  const query = typeof limit === "number" ? `?limit=${Math.max(1, Math.floor(limit))}` : "";
  return request<MealRecordsApiResponse>(`/api/v1/meal/records${query}`);
}

export async function getMealDailySummary(date?: string): Promise<MealDailySummaryApiResponse> {
  const query = date ? `?date=${encodeURIComponent(date)}` : "";
  return request<MealDailySummaryApiResponse>(`/api/v1/meal/daily-summary${query}`);
}

export async function getMealWeeklySummary(weekStart: string): Promise<MealWeeklySummaryApiResponse> {
  const query = `?week_start=${encodeURIComponent(weekStart)}`;
  return request<MealWeeklySummaryApiResponse>(`/api/v1/meal/weekly-summary${query}`);
}

export async function parseReport(payload: {
  source: "pasted_text";
  text: string;
}): Promise<ReportParseApiResponse> {
  return request<ReportParseApiResponse>("/api/v1/reports/parse", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function generateRecommendation(): Promise<RecommendationGenerateApiResponse> {
  return request<RecommendationGenerateApiResponse>("/api/v1/recommendations/generate", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function generateSuggestionFromReport(payload: {
  source?: "pasted_text";
  text: string;
}): Promise<SuggestionGenerateApiResponse> {
  return request<SuggestionGenerateApiResponse>("/api/v1/suggestions/generate-from-report", {
    method: "POST",
    body: JSON.stringify({ source: "pasted_text", ...payload }),
  });
}

export async function listSuggestions(options?: {
  limit?: number;
  scope?: "self" | "household";
  sourceUserId?: string;
}): Promise<SuggestionListApiResponse> {
  const params = new URLSearchParams();
  if (typeof options?.limit === "number") params.set("limit", String(Math.max(1, Math.floor(options.limit))));
  if (options?.scope) params.set("scope", options.scope);
  if (options?.sourceUserId) params.set("source_user_id", options.sourceUserId);
  const query = params.toString();
  return request<SuggestionListApiResponse>(`/api/v1/suggestions${query ? `?${query}` : ""}`);
}

export async function getSuggestion(
  suggestionId: string,
  options?: { scope?: "self" | "household" },
): Promise<SuggestionDetailApiResponse> {
  const params = new URLSearchParams();
  if (options?.scope) params.set("scope", options.scope);
  const query = params.toString();
  return request<SuggestionDetailApiResponse>(
    `/api/v1/suggestions/${suggestionId}${query ? `?${query}` : ""}`,
  );
}

export async function generateReminders(): Promise<ReminderGenerateApiResponse> {
  return request<ReminderGenerateApiResponse>("/api/v1/reminders/generate", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function listReminders(): Promise<ReminderListApiResponse> {
  return request<ReminderListApiResponse>("/api/v1/reminders");
}

export async function confirmReminder(
  eventId: string,
  confirmed: boolean,
): Promise<ReminderConfirmApiResponse> {
  return request<ReminderConfirmApiResponse>(`/api/v1/reminders/${eventId}/confirm`, {
    method: "POST",
    body: JSON.stringify({ confirmed }),
  });
}

export async function listReminderNotificationPreferences(): Promise<ReminderNotificationPreferenceListResponse> {
  return request<ReminderNotificationPreferenceListResponse>("/api/v1/reminder-notification-preferences");
}

export async function getMobilityReminderSettings(): Promise<MobilityReminderSettingsEnvelopeResponse> {
  return request<MobilityReminderSettingsEnvelopeResponse>("/api/v1/reminders/mobility-settings");
}

export async function updateMobilityReminderSettings(payload: {
  enabled: boolean;
  interval_minutes: number;
  active_start_time: string;
  active_end_time: string;
}): Promise<MobilityReminderSettingsEnvelopeResponse> {
  return request<MobilityReminderSettingsEnvelopeResponse>("/api/v1/reminders/mobility-settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function updateReminderNotificationPreferences(payload: {
  rules: Array<{ channel: string; offset_minutes: number; enabled: boolean }>;
}): Promise<ReminderNotificationPreferenceListResponse> {
  return request<ReminderNotificationPreferenceListResponse>("/api/v1/reminder-notification-preferences/default", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function listReminderNotificationEndpoints(): Promise<ReminderNotificationEndpointListResponse> {
  return request<ReminderNotificationEndpointListResponse>("/api/v1/reminder-notification-endpoints");
}

export async function updateReminderNotificationEndpoints(payload: {
  endpoints: Array<{ channel: string; destination: string; verified: boolean }>;
}): Promise<ReminderNotificationEndpointListResponse> {
  return request<ReminderNotificationEndpointListResponse>("/api/v1/reminder-notification-endpoints", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function listReminderNotificationSchedules(
  reminderId: string,
): Promise<ScheduledReminderNotificationListResponse> {
  return request<ScheduledReminderNotificationListResponse>(`/api/v1/reminders/${reminderId}/notification-schedules`);
}

export async function listReminderNotificationLogs(reminderId: string): Promise<ReminderNotificationLogListResponse> {
  return request<ReminderNotificationLogListResponse>(`/api/v1/reminders/${reminderId}/notification-logs`);
}

export async function listMedicationRegimens(): Promise<MedicationRegimenListApiResponse> {
  return request<MedicationRegimenListApiResponse>("/api/v1/medications/regimens");
}

export async function createMedicationRegimen(payload: {
  medication_name: string;
  dosage_text: string;
  timing_type: "pre_meal" | "post_meal" | "fixed_time";
  offset_minutes?: number;
  slot_scope?: Array<"breakfast" | "lunch" | "dinner" | "snack">;
  fixed_time?: string | null;
  max_daily_doses?: number;
  active?: boolean;
}): Promise<MedicationRegimenEnvelopeApiResponse> {
  return request<MedicationRegimenEnvelopeApiResponse>("/api/v1/medications/regimens", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateMedicationRegimen(
  regimenId: string,
  payload: {
    medication_name?: string;
    dosage_text?: string;
    timing_type?: "pre_meal" | "post_meal" | "fixed_time";
    offset_minutes?: number;
    slot_scope?: Array<"breakfast" | "lunch" | "dinner" | "snack">;
    fixed_time?: string | null;
    max_daily_doses?: number;
    active?: boolean;
  },
): Promise<MedicationRegimenEnvelopeApiResponse> {
  return request<MedicationRegimenEnvelopeApiResponse>(`/api/v1/medications/regimens/${regimenId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteMedicationRegimen(regimenId: string): Promise<{ ok: boolean; deleted: boolean }> {
  return request<{ ok: boolean; deleted: boolean }>(`/api/v1/medications/regimens/${regimenId}`, {
    method: "DELETE",
  });
}

export async function createMedicationAdherenceEvent(payload: {
  regimen_id: string;
  reminder_id?: string;
  status: "taken" | "missed" | "skipped" | "unknown";
  scheduled_at: string;
  taken_at?: string | null;
  source?: "manual" | "reminder_confirm" | "imported";
  metadata?: Record<string, unknown>;
}): Promise<{ event: Record<string, unknown> }> {
  return request<{ event: Record<string, unknown> }>("/api/v1/medications/adherence-events", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMedicationAdherenceMetrics(params?: {
  from?: string;
  to?: string;
}): Promise<MedicationAdherenceMetricsApiResponse> {
  const query = new URLSearchParams();
  if (params?.from) query.set("from", params.from);
  if (params?.to) query.set("to", params.to);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<MedicationAdherenceMetricsApiResponse>(`/api/v1/medications/adherence-metrics${suffix}`);
}

export async function createSymptomCheckIn(payload: {
  severity: number;
  symptom_codes?: string[];
  free_text?: string;
  context?: Record<string, unknown>;
}): Promise<SymptomCheckInEnvelopeApiResponse> {
  return request<SymptomCheckInEnvelopeApiResponse>("/api/v1/symptoms/check-ins", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listSymptomCheckIns(params?: {
  from?: string;
  to?: string;
  limit?: number;
}): Promise<SymptomCheckInListApiResponse> {
  const query = new URLSearchParams();
  if (params?.from) query.set("from", params.from);
  if (params?.to) query.set("to", params.to);
  if (typeof params?.limit === "number") query.set("limit", String(Math.max(1, Math.floor(params.limit))));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<SymptomCheckInListApiResponse>(`/api/v1/symptoms/check-ins${suffix}`);
}

export async function getSymptomSummary(params?: {
  from?: string;
  to?: string;
}): Promise<SymptomSummaryApiResponse> {
  const query = new URLSearchParams();
  if (params?.from) query.set("from", params.from);
  if (params?.to) query.set("to", params.to);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<SymptomSummaryApiResponse>(`/api/v1/symptoms/summary${suffix}`);
}

export async function generateClinicalCard(payload?: {
  start_date?: string;
  end_date?: string;
  format?: "sectioned" | "soap";
}): Promise<ClinicalCardEnvelopeApiResponse> {
  return request<ClinicalCardEnvelopeApiResponse>("/api/v1/clinical-cards/generate", {
    method: "POST",
    body: JSON.stringify(payload ?? {}),
  });
}

export async function listClinicalCards(limit = 20): Promise<ClinicalCardListApiResponse> {
  return request<ClinicalCardListApiResponse>(`/api/v1/clinical-cards?limit=${Math.max(1, Math.floor(limit))}`);
}

export async function getClinicalCard(cardId: string): Promise<ClinicalCardEnvelopeApiResponse> {
  return request<ClinicalCardEnvelopeApiResponse>(`/api/v1/clinical-cards/${cardId}`);
}

export async function listMetricTrends(metric?: string[]): Promise<MetricTrendListApiResponse> {
  const query = new URLSearchParams();
  for (const item of metric ?? []) query.append("metric", item);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<MetricTrendListApiResponse>(`/api/v1/metrics/trends${suffix}`);
}
