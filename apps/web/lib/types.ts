export type AccountRole = "member" | "admin";
export type ProfileMode = "self" | "caregiver";

export interface SessionUser {
  user_id: string;
  email: string;
  account_role: AccountRole;
  scopes: string[];
  profile_mode: ProfileMode;
  display_name: string;
}

export interface AuthLoginResponse {
  user: SessionUser;
  session: {
    session_id: string;
    issued_at: string;
  };
}

export interface WorkflowExecutionResult {
  workflow_name: string;
  request_id: string;
  correlation_id: string;
  replayed?: boolean;
  timeline_events?: Array<Record<string, unknown>>;
  tool_results?: Array<Record<string, unknown>>;
  handoffs?: Array<Record<string, unknown>>;
}

export interface WorkflowListApiResponse {
  items: Array<Record<string, unknown>>;
}

export interface AlertTriggerApiResponse {
  tool_result: Record<string, unknown>;
  outbox_timeline: Array<Record<string, unknown>>;
  workflow: WorkflowExecutionResult;
}

export interface AlertTimelineApiResponse {
  alert_id: string;
  outbox_timeline: Array<Record<string, unknown>>;
}

export interface MealAnalyzeApiResponse {
  vision_result: Record<string, unknown>;
  meal_record: Record<string, unknown>;
  output_envelope: Record<string, unknown> | null;
  workflow: WorkflowExecutionResult;
}

export interface MealRecordsApiResponse {
  records: Array<Record<string, unknown>>;
}

export interface ReportParseApiResponse {
  readings: Array<Record<string, unknown>>;
  snapshot: {
    biomarkers: Record<string, number>;
    risk_flags: string[];
  };
}

export interface RecommendationGenerateApiResponse {
  recommendation: Record<string, unknown>;
  workflow: WorkflowExecutionResult;
}

export interface ReminderEventView {
  id: string;
  medication_name: string;
  dosage_text: string;
  scheduled_at: string;
  status: "sent" | "acknowledged" | "missed";
  meal_confirmation: "yes" | "no" | "unknown";
}

export interface ReminderMetrics {
  reminders_sent: number;
  meal_confirmed_yes: number;
  meal_confirmed_no: number;
  meal_confirmation_rate: number;
}

export interface ReminderListApiResponse {
  reminders: ReminderEventView[];
  metrics: ReminderMetrics;
}

export interface ReminderGenerateApiResponse extends ReminderListApiResponse {}

export interface ReminderConfirmApiResponse {
  event: ReminderEventView;
  metrics: ReminderMetrics;
}
