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

export interface AuthSessionListItem {
  session_id: string;
  issued_at: string;
  is_current: boolean;
}

export interface AuthSessionListResponse {
  sessions: AuthSessionListItem[];
}

export interface AuthSessionRevokeResponse {
  ok: boolean;
  revoked: boolean;
}

export interface AuthSessionRevokeOthersResponse {
  ok: boolean;
  revoked_count: number;
}

export interface AuthProfileUpdateResponse {
  user: SessionUser;
}

export interface AuthPasswordUpdateResponse {
  ok: boolean;
  revoked_other_sessions: number;
}

export interface AuthAuditEvent {
  event_id: string;
  event_type: string;
  email: string;
  user_id?: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface AuthAuditEventListResponse {
  items: AuthAuditEvent[];
}

export interface Household {
  household_id: string;
  name: string;
  owner_user_id: string;
  created_at: string;
}

export interface HouseholdMember {
  user_id: string;
  display_name: string;
  role: "owner" | "member";
  joined_at: string;
}

export interface HouseholdBundleApiResponse {
  household: Household | null;
  members: HouseholdMember[];
  active_household_id?: string | null;
}

export interface HouseholdInvite {
  invite_id: string;
  household_id: string;
  code: string;
  created_by_user_id: string;
  created_at: string;
  expires_at: string;
  max_uses: number;
  uses: number;
}

export interface HouseholdInviteCreateResponse {
  invite: HouseholdInvite;
}

export interface HouseholdMembersResponse {
  members: HouseholdMember[];
}

export interface HouseholdLeaveResponse {
  ok: boolean;
  left_household_id: string;
}

export interface HouseholdMemberRemoveResponse {
  ok: boolean;
  removed_user_id: string;
}

export interface HouseholdActiveUpdateResponse {
  ok: boolean;
  active_household_id: string | null;
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
  summary: {
    meal_record_id: string;
    meal_name: string;
    confidence: number;
    identification_method: string;
    estimated_calories: number;
    portion_size: string;
    needs_manual_review: boolean;
    flags: string[];
    portion_notes: string[];
    captured_at: string;
  };
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

export interface SuggestionItemApi {
  suggestion_id: string;
  created_at: string;
  disclaimer: string;
  report_parse: {
    readings: Array<Record<string, unknown>>;
    snapshot: {
      biomarkers: Record<string, number>;
      risk_flags: string[];
    };
  };
  recommendation: Record<string, unknown>;
  workflow: WorkflowExecutionResult;
}

export interface SuggestionGenerateApiResponse {
  suggestion: SuggestionItemApi;
}

export interface SuggestionListApiResponse {
  items: SuggestionItemApi[];
}

export interface SuggestionDetailApiResponse {
  suggestion: SuggestionItemApi;
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
