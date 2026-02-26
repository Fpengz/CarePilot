import type {
  AlertTimelineApiResponse,
  AlertTriggerApiResponse,
  AuthAuditEventListResponse,
  AuthLoginResponse,
  AuthPasswordUpdateResponse,
  AuthProfileUpdateResponse,
  AuthSessionListResponse,
  AuthSessionRevokeOthersResponse,
  AuthSessionRevokeResponse,
  MealAnalyzeApiResponse,
  MealRecordsApiResponse,
  RecommendationGenerateApiResponse,
  ReminderConfirmApiResponse,
  ReminderGenerateApiResponse,
  ReminderListApiResponse,
  ReportParseApiResponse,
  SessionUser,
  WorkflowExecutionResult,
  WorkflowListApiResponse,
} from "@/lib/types";

// Default to localhost (not 127.0.0.1) so SameSite=Lax auth cookies remain same-site
// when the web app is served from http://localhost:3000 in local development.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
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
    throw new Error(`API ${response.status}: ${text}`);
  }
  return (await response.json()) as T;
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

export async function analyzeMeal(formData: FormData): Promise<MealAnalyzeApiResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/meal/analyze`, {
    method: "POST",
    body: formData,
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API ${response.status}: ${text}`);
  }
  return (await response.json()) as MealAnalyzeApiResponse;
}

export async function listMealRecords(limit?: number): Promise<MealRecordsApiResponse> {
  const query = typeof limit === "number" ? `?limit=${Math.max(1, Math.floor(limit))}` : "";
  return request<MealRecordsApiResponse>(`/api/v1/meal/records${query}`);
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
