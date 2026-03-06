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

export interface HealthProfileCondition {
  name: string;
  severity: string;
}

export interface HealthProfileMedication {
  name: string;
  dosage: string;
  contraindications: string[];
}

export interface HealthProfileCompleteness {
  state: "needs_profile" | "partial" | "ready";
  missing_fields: string[];
}

export interface HealthProfile {
  age: number | null;
  locale: string;
  height_cm: number | null;
  weight_kg: number | null;
  bmi: number | null;
  daily_sodium_limit_mg: number;
  daily_sugar_limit_g: number;
  daily_protein_target_g: number;
  daily_fiber_target_g: number;
  target_calories_per_day: number | null;
  macro_focus: string[];
  conditions: HealthProfileCondition[];
  medications: HealthProfileMedication[];
  allergies: string[];
  nutrition_goals: string[];
  preferred_cuisines: string[];
  disliked_ingredients: string[];
  budget_tier: "budget" | "moderate" | "flexible";
  fallback_mode: boolean;
  completeness: HealthProfileCompleteness;
  updated_at?: string | null;
}

export interface HealthProfileResponse {
  profile: HealthProfile;
}

export interface GuidedHealthStep {
  id: string;
  title: string;
  description: string;
  fields: string[];
}

export interface HealthProfileOnboardingState {
  current_step: string;
  completed_steps: string[];
  is_complete: boolean;
  updated_at?: string | null;
}

export interface HealthProfileOnboardingResponse {
  onboarding: HealthProfileOnboardingState;
  profile: HealthProfile;
  steps: GuidedHealthStep[];
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

export interface HouseholdCareContext {
  viewer_user_id: string;
  subject_user_id: string;
  household_id: string;
}

export interface HouseholdCareMembersResponse {
  viewer_user_id: string;
  household_id: string;
  members: HouseholdMember[];
}

export interface HouseholdCareProfileResponse {
  context: HouseholdCareContext;
  profile: HealthProfile;
}

export interface HouseholdCareMealSummaryResponse {
  context: HouseholdCareContext;
  summary: MealDailySummaryApiResponse;
}

export interface HouseholdCareReminderListResponse {
  context: HouseholdCareContext;
  reminders: ReminderEventView[];
  metrics: ReminderMetrics;
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

export interface DailyNutritionTotals {
  calories: number;
  sugar_g: number;
  sodium_mg: number;
  protein_g: number;
  fiber_g: number;
}

export interface DailyNutritionInsight {
  code: string;
  title: string;
  summary: string;
  actions: string[];
}

export interface MealDailySummaryApiResponse {
  date: string;
  meal_count: number;
  last_logged_at: string | null;
  consumed: DailyNutritionTotals;
  targets: DailyNutritionTotals;
  remaining: DailyNutritionTotals;
  insights: DailyNutritionInsight[];
  recommendation_hints: string[];
}

export interface MealWeeklySummaryDayApiResponse {
  meal_count: number;
  calories: number;
  sugar_g: number;
  sodium_mg: number;
}

export interface MealWeeklySummaryApiResponse {
  week_start: string;
  week_end: string;
  meal_count: number;
  totals: DailyNutritionTotals;
  daily_breakdown: Record<string, MealWeeklySummaryDayApiResponse>;
  pattern_flags: string[];
}

export interface ReportParseApiResponse {
  readings: Array<Record<string, unknown>>;
  snapshot: {
    biomarkers: Record<string, number>;
    risk_flags: string[];
  };
  symptom_summary: SymptomSummaryApiResponse;
  symptom_window: {
    from: string;
    to: string;
    limit: number;
  };
}

export interface RecommendationGenerateApiResponse {
  recommendation: Record<string, unknown>;
  workflow: WorkflowExecutionResult;
}

export type RecommendationInteractionEventType =
  | "viewed"
  | "accepted"
  | "dismissed"
  | "swap_selected"
  | "meal_logged_after_recommendation"
  | "ignored";

export interface AgentCandidateScores {
  preference_fit: number;
  temporal_fit: number;
  adherence_likelihood: number;
  health_gain: number;
  substitution_deviation_penalty: number;
  total_score: number;
}

export interface AgentHealthDelta {
  calories: number;
  sugar_g: number;
  sodium_mg: number;
}

export interface RecommendationAgentCard {
  candidate_id: string;
  slot: "breakfast" | "lunch" | "dinner" | "snack";
  title: string;
  venue_type: string;
  why_it_fits: string[];
  caution_notes: string[];
  confidence: number;
  scores: AgentCandidateScores;
  health_gain_summary: AgentHealthDelta;
}

export interface RecommendationAgentSourceMeal {
  meal_id: string;
  title: string;
  slot: "breakfast" | "lunch" | "dinner" | "snack";
}

export interface RecommendationSubstitutionAlternative {
  candidate_id: string;
  title: string;
  venue_type: string;
  health_delta: AgentHealthDelta;
  taste_distance: number;
  reasoning: string;
  confidence: number;
}

export interface RecommendationSubstitutionPlan {
  source_meal: RecommendationAgentSourceMeal;
  alternatives: RecommendationSubstitutionAlternative[];
  blocked_reason: string | null;
}

export interface RecommendationAgentProfileState {
  completeness_state: string;
  bmi: number | null;
  target_calories_per_day: number | null;
  macro_focus: string[];
}

export interface RecommendationAgentTemporalContext {
  current_slot: "breakfast" | "lunch" | "dinner" | "snack";
  generated_at: string;
  meal_history_count: number;
  interaction_count: number;
  recent_repeat_titles: string[];
  slot_history_counts: Record<string, number>;
}

export interface RecommendationInteractionApiResponse {
  ok: boolean;
  interaction: Record<string, unknown>;
  preference_snapshot: Record<string, unknown>;
}

export interface RecommendationSubstitutionApiResponse extends RecommendationSubstitutionPlan {}

export interface RecommendationAgentApiResponse {
  profile_state: RecommendationAgentProfileState;
  temporal_context: RecommendationAgentTemporalContext;
  recommendations: Record<string, RecommendationAgentCard>;
  substitutions: RecommendationSubstitutionPlan | null;
  fallback_mode: boolean;
  data_sources: Record<string, unknown>;
  constraints_applied: string[];
  workflow: WorkflowExecutionResult;
}

export interface SuggestionItemApi {
  suggestion_id: string;
  created_at: string;
  source_user_id: string;
  source_display_name: string;
  disclaimer: string;
  safety: {
    decision: "allow" | "modify" | "refuse" | "escalate" | "ask_clarification";
    reasons: string[];
    required_actions: string[];
    redactions: string[];
  };
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

export interface DailySuggestionCard {
  slot: "breakfast" | "lunch" | "dinner" | "snack";
  title: string;
  venue_type: string;
  why_it_fits: string[];
  caution_notes: string[];
  confidence: number;
}

export interface DailySuggestionsResponse {
  profile: HealthProfile;
  bundle: {
    locale: string;
    generated_at: string;
    data_sources: {
      meal_history_count: number;
      has_clinical_snapshot: boolean;
      biomarker_count: number;
      [key: string]: unknown;
    };
    warnings: string[];
    suggestions: Record<string, DailySuggestionCard>;
  };
}

export interface SuggestionListApiResponse {
  items: SuggestionItemApi[];
}

export interface SuggestionDetailApiResponse {
  suggestion: SuggestionItemApi;
}

export interface ReminderEventView {
  reminder_type: "medication" | "mobility";
  title: string;
  body: string | null;
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

export interface MobilityReminderSettings {
  enabled: boolean;
  interval_minutes: number;
  active_start_time: string;
  active_end_time: string;
}

export interface MobilityReminderSettingsEnvelopeResponse {
  settings: MobilityReminderSettings;
}

export type ReminderNotificationChannel = "in_app" | "email" | "sms" | "push" | "telegram" | "whatsapp" | "wechat";

export interface ReminderNotificationPreferenceRule {
  id: string;
  scope_type: "default" | "reminder_type";
  scope_key?: string | null;
  channel: ReminderNotificationChannel;
  offset_minutes: number;
  enabled: boolean;
  updated_at: string;
}

export interface ReminderNotificationPreferenceListResponse {
  preferences: ReminderNotificationPreferenceRule[];
}

export interface ReminderNotificationEndpoint {
  id: string;
  channel: ReminderNotificationChannel;
  destination: string;
  verified: boolean;
  updated_at: string;
}

export interface ReminderNotificationEndpointListResponse {
  endpoints: ReminderNotificationEndpoint[];
}

export interface ScheduledReminderNotificationItem {
  id: string;
  reminder_id: string;
  channel: ReminderNotificationChannel;
  trigger_at: string;
  offset_minutes: number;
  status: "pending" | "queued" | "processing" | "retry_scheduled" | "delivered" | "dead_letter" | "cancelled";
  attempt_count: number;
  delivered_at?: string | null;
  last_error?: string | null;
}

export interface ScheduledReminderNotificationListResponse {
  items: ScheduledReminderNotificationItem[];
}

export interface ReminderNotificationLogItem {
  id: string;
  scheduled_notification_id: string;
  channel: ReminderNotificationChannel;
  attempt_number: number;
  event_type: "scheduled" | "queued" | "dispatch_started" | "delivered" | "retry_scheduled" | "dead_lettered" | "cancelled";
  error_message?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ReminderNotificationLogListResponse {
  items: ReminderNotificationLogItem[];
}

export interface MedicationRegimenApi {
  id: string;
  medication_name: string;
  dosage_text: string;
  timing_type: "pre_meal" | "post_meal" | "fixed_time";
  offset_minutes: number;
  slot_scope: Array<"breakfast" | "lunch" | "dinner" | "snack">;
  fixed_time?: string | null;
  max_daily_doses: number;
  active: boolean;
}

export interface MedicationRegimenListApiResponse {
  items: MedicationRegimenApi[];
}

export interface MedicationRegimenEnvelopeApiResponse {
  regimen: MedicationRegimenApi;
}

export interface MedicationAdherenceEventApi {
  id: string;
  regimen_id: string;
  reminder_id?: string | null;
  status: "taken" | "missed" | "skipped" | "unknown";
  scheduled_at: string;
  taken_at?: string | null;
  source: "manual" | "reminder_confirm" | "imported";
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface MedicationAdherenceMetricsApiResponse {
  totals: {
    events: number;
    taken: number;
    missed: number;
    skipped: number;
    adherence_rate: number;
  };
  events: MedicationAdherenceEventApi[];
}

export interface SymptomCheckInApi {
  id: string;
  recorded_at: string;
  severity: number;
  symptom_codes: string[];
  free_text?: string | null;
  context: Record<string, unknown>;
  safety: {
    decision: string;
    reasons: string[];
    required_actions: string[];
    redactions: string[];
  };
}

export interface SymptomCheckInListApiResponse {
  items: SymptomCheckInApi[];
}

export interface SymptomCheckInEnvelopeApiResponse {
  item: SymptomCheckInApi;
}

export interface SymptomSummaryApiResponse {
  total_count: number;
  average_severity: number;
  red_flag_count: number;
  top_symptoms: Array<{ code: string; count: number }>;
  latest_recorded_at?: string | null;
}

export interface ClinicalCardApi {
  id: string;
  created_at: string;
  start_date: string;
  end_date: string;
  format: "sectioned" | "soap";
  sections: Record<string, string>;
  deltas: Record<string, number>;
  trends: Record<string, Record<string, unknown>>;
  provenance: Record<string, unknown>;
}

export interface ClinicalCardListApiResponse {
  items: ClinicalCardApi[];
}

export interface ClinicalCardEnvelopeApiResponse {
  card: ClinicalCardApi;
}

export interface MetricTrendApi {
  metric: string;
  points: Array<{ timestamp: string; value: number }>;
  delta: number;
  percent_change?: number | null;
  slope_per_point: number;
  direction: "increase" | "decrease" | "flat";
}

export interface MetricTrendListApiResponse {
  items: MetricTrendApi[];
}
