"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";

import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { useSession } from "@/components/app/session-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  generateSuggestionFromReport,
  getDailyAgentRecommendations,
  getDailySuggestions,
  getHealthProfile,
  getMealSubstitutions,
  getAlertTimeline,
  getWorkflow,
  listMealRecords,
  listReminders,
  recordRecommendationInteraction,
  listSuggestions,
  listWorkflows,
  updateHealthProfile,
} from "@/lib/api";
import type {
  DailySuggestionsResponse,
  HealthProfile,
  RecommendationAgentApiResponse,
  RecommendationInteractionEventType,
  ReminderEventView,
  SuggestionGenerateApiResponse,
  SuggestionListApiResponse,
  WorkflowExecutionResult,
} from "@/lib/types";

type Scope = "self" | "household";

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function isoDay(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString().slice(0, 10);
}

function csvToList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function numberDraft(value: number | null | undefined): string {
  return value == null ? "" : String(value);
}

function toOptionalNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function conditionsText(profile: HealthProfile | null): string {
  return (profile?.conditions ?? []).map((item) => `${item.name}:${item.severity}`).join(", ");
}

function medicationsText(profile: HealthProfile | null): string {
  return (profile?.medications ?? []).map((item) => `${item.name}:${item.dosage}`).join(", ");
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatSigned(value: number, unit: string): string {
  const rounded = Math.round(value);
  return `${rounded > 0 ? "+" : ""}${rounded} ${unit}`;
}

export function DashboardIterationWorkspace() {
  const { status, user } = useSession();

  const [reportText, setReportText] = useState("HbA1c 7.2 LDL 4.1 BP 148/92");
  const [suggestionBusy, setSuggestionBusy] = useState(false);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);
  const [suggestionResult, setSuggestionResult] = useState<SuggestionGenerateApiResponse | null>(null);

  const [scope, setScope] = useState<Scope>("self");
  const [overviewBusy, setOverviewBusy] = useState(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [mealRecords, setMealRecords] = useState<Array<Record<string, unknown>>>([]);
  const [suggestionItems, setSuggestionItems] = useState<SuggestionListApiResponse["items"]>([]);
  const [reminders, setReminders] = useState<ReminderEventView[]>([]);
  const [confirmationRate, setConfirmationRate] = useState(0);

  const [workflowsBusy, setWorkflowsBusy] = useState(false);
  const [workflowsError, setWorkflowsError] = useState<string | null>(null);
  const [workflowItems, setWorkflowItems] = useState<Array<Record<string, unknown>>>([]);
  const [selectedCorrelationId, setSelectedCorrelationId] = useState("");
  const [workflowDetail, setWorkflowDetail] = useState<WorkflowExecutionResult | null>(null);

  const [alertId, setAlertId] = useState("");
  const [alertBusy, setAlertBusy] = useState(false);
  const [alertError, setAlertError] = useState<string | null>(null);
  const [alertTimeline, setAlertTimeline] = useState<Array<Record<string, unknown>>>([]);

  const [profileBusy, setProfileBusy] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [agentBusy, setAgentBusy] = useState(false);
  const [agentError, setAgentError] = useState<string | null>(null);
  const [agentActionId, setAgentActionId] = useState<string | null>(null);
  const [healthProfile, setHealthProfile] = useState<HealthProfile | null>(null);
  const [dailySuggestions, setDailySuggestions] = useState<DailySuggestionsResponse | null>(null);
  const [agentFeed, setAgentFeed] = useState<RecommendationAgentApiResponse | null>(null);
  const [profileAge, setProfileAge] = useState("");
  const [profileLocale, setProfileLocale] = useState("en-SG");
  const [profileHeightCm, setProfileHeightCm] = useState("");
  const [profileWeightKg, setProfileWeightKg] = useState("");
  const [profileSodiumLimit, setProfileSodiumLimit] = useState("1800");
  const [profileSugarLimit, setProfileSugarLimit] = useState("30");
  const [profileTargetCalories, setProfileTargetCalories] = useState("");
  const [profileMacroFocus, setProfileMacroFocus] = useState("higher_protein, lower_sugar");
  const [profileGoals, setProfileGoals] = useState("lower_sugar, heart_health");
  const [profileCuisines, setProfileCuisines] = useState("teochew, local");
  const [profileAllergies, setProfileAllergies] = useState("");
  const [profileDislikes, setProfileDislikes] = useState("");
  const [profileConditions, setProfileConditions] = useState("");
  const [profileMedications, setProfileMedications] = useState("");
  const [profileBudget, setProfileBudget] = useState<"budget" | "moderate" | "flexible">("moderate");

  async function runUnifiedSuggestionFlow() {
    setSuggestionBusy(true);
    setSuggestionError(null);
    try {
      const result = await generateSuggestionFromReport({ text: reportText });
      setSuggestionResult(result);
    } catch (error) {
      setSuggestionError(toErrorMessage(error));
    } finally {
      setSuggestionBusy(false);
    }
  }

  function syncProfileDraft(profile: HealthProfile) {
    setProfileAge(numberDraft(profile.age));
    setProfileLocale(profile.locale || "en-SG");
    setProfileHeightCm(numberDraft(profile.height_cm));
    setProfileWeightKg(numberDraft(profile.weight_kg));
    setProfileSodiumLimit(String(profile.daily_sodium_limit_mg));
    setProfileSugarLimit(String(profile.daily_sugar_limit_g));
    setProfileTargetCalories(numberDraft(profile.target_calories_per_day));
    setProfileMacroFocus(profile.macro_focus.join(", "));
    setProfileGoals(profile.nutrition_goals.join(", "));
    setProfileCuisines(profile.preferred_cuisines.join(", "));
    setProfileAllergies(profile.allergies.join(", "));
    setProfileDislikes(profile.disliked_ingredients.join(", "));
    setProfileConditions(conditionsText(profile));
    setProfileMedications(medicationsText(profile));
    setProfileBudget(profile.budget_tier);
  }

  const refreshAgentFeed = useCallback(async () => {
    setAgentBusy(true);
    setAgentError(null);
    try {
      const [agentResponse, dailyResponse] = await Promise.all([getDailyAgentRecommendations(), getDailySuggestions()]);
      setAgentFeed(agentResponse);
      setDailySuggestions(dailyResponse);
    } catch (error) {
      setAgentError(toErrorMessage(error));
    } finally {
      setAgentBusy(false);
    }
  }, []);

  const loadPersonalization = useCallback(async () => {
    setProfileBusy(true);
    setProfileError(null);
    setAgentBusy(true);
    setAgentError(null);
    try {
      const [profileResponse, dailyResponse, agentResponse] = await Promise.all([
        getHealthProfile(),
        getDailySuggestions(),
        getDailyAgentRecommendations(),
      ]);
      setHealthProfile(profileResponse.profile);
      syncProfileDraft(profileResponse.profile);
      setDailySuggestions(dailyResponse);
      setAgentFeed(agentResponse);
    } catch (error) {
      const message = toErrorMessage(error);
      setProfileError(message);
      setAgentError(message);
    } finally {
      setProfileBusy(false);
      setAgentBusy(false);
    }
  }, []);

  async function saveHealthProfileDraft() {
    setProfileBusy(true);
    setProfileError(null);
    try {
      const updated = await updateHealthProfile({
        age: toOptionalNumber(profileAge),
        locale: profileLocale.trim(),
        height_cm: toOptionalNumber(profileHeightCm),
        weight_kg: toOptionalNumber(profileWeightKg),
        daily_sodium_limit_mg: toOptionalNumber(profileSodiumLimit) ?? undefined,
        daily_sugar_limit_g: toOptionalNumber(profileSugarLimit) ?? undefined,
        target_calories_per_day: toOptionalNumber(profileTargetCalories),
        macro_focus: csvToList(profileMacroFocus),
        nutrition_goals: csvToList(profileGoals),
        preferred_cuisines: csvToList(profileCuisines),
        allergies: csvToList(profileAllergies),
        disliked_ingredients: csvToList(profileDislikes),
        conditions: csvToList(profileConditions).map((item) => {
          const [name, severity = "Medium"] = item.split(":").map((part) => part.trim());
          return { name, severity };
        }),
        medications: csvToList(profileMedications).map((item) => {
          const [name, dosage = "unspecified"] = item.split(":").map((part) => part.trim());
          return { name, dosage, contraindications: [] };
        }),
        budget_tier: profileBudget,
      });
      setHealthProfile(updated.profile);
      syncProfileDraft(updated.profile);
      await refreshAgentFeed();
    } catch (error) {
      setProfileError(toErrorMessage(error));
    } finally {
      setProfileBusy(false);
    }
  }

  async function submitRecommendationFeedback(args: {
    eventType: RecommendationInteractionEventType;
    candidateId: string;
    slot: "breakfast" | "lunch" | "dinner" | "snack";
    sourceMealId?: string;
    selectedMealId?: string;
  }) {
    if (!agentFeed) return;
    const actionId = `${args.eventType}:${args.candidateId}`;
    setAgentActionId(actionId);
    setAgentError(null);
    try {
      await recordRecommendationInteraction({
        recommendation_id: agentFeed.workflow.request_id,
        candidate_id: args.candidateId,
        event_type: args.eventType,
        slot: args.slot,
        source_meal_id: args.sourceMealId,
        selected_meal_id: args.selectedMealId,
        metadata: { surface: "dashboard_agent" },
      });
      await refreshAgentFeed();
    } catch (error) {
      setAgentError(toErrorMessage(error));
    } finally {
      setAgentActionId(null);
    }
  }

  async function refreshSubstitutions(sourceMealId: string) {
    setAgentActionId(`refresh-substitutions:${sourceMealId}`);
    setAgentError(null);
    try {
      const plan = await getMealSubstitutions({ source_meal_id: sourceMealId, limit: 3 });
      setAgentFeed((current) => (current ? { ...current, substitutions: plan } : current));
    } catch (error) {
      setAgentError(toErrorMessage(error));
    } finally {
      setAgentActionId(null);
    }
  }

  async function loadHouseholdAwareViews() {
    setOverviewBusy(true);
    setOverviewError(null);
    try {
      const [meals, suggestions, reminderState] = await Promise.all([
        listMealRecords(30),
        listSuggestions({ scope, limit: 30 }),
        listReminders(),
      ]);
      setMealRecords(meals.records);
      setSuggestionItems(suggestions.items);
      setReminders(reminderState.reminders);
      setConfirmationRate(reminderState.metrics.meal_confirmation_rate);
    } catch (error) {
      setOverviewError(toErrorMessage(error));
    } finally {
      setOverviewBusy(false);
    }
  }

  async function loadWorkflowList() {
    setWorkflowsBusy(true);
    setWorkflowsError(null);
    try {
      const data = await listWorkflows();
      setWorkflowItems(data.items);
      const firstCorrelation = data.items.find((item) => typeof item.correlation_id === "string")?.correlation_id;
      if (typeof firstCorrelation === "string") {
        setSelectedCorrelationId(firstCorrelation);
      }
    } catch (error) {
      setWorkflowsError(toErrorMessage(error));
    } finally {
      setWorkflowsBusy(false);
    }
  }

  async function loadSelectedWorkflow() {
    if (!selectedCorrelationId.trim()) return;
    setWorkflowsBusy(true);
    setWorkflowsError(null);
    try {
      const detail = await getWorkflow(selectedCorrelationId.trim());
      setWorkflowDetail(detail);
    } catch (error) {
      setWorkflowsError(toErrorMessage(error));
    } finally {
      setWorkflowsBusy(false);
    }
  }

  async function loadAlertTimeline() {
    if (!alertId.trim()) return;
    setAlertBusy(true);
    setAlertError(null);
    try {
      const data = await getAlertTimeline(alertId.trim());
      setAlertTimeline(data.outbox_timeline as Array<Record<string, unknown>>);
    } catch (error) {
      setAlertError(toErrorMessage(error));
    } finally {
      setAlertBusy(false);
    }
  }

  const trendBars = useMemo(() => {
    const today = new Date();
    const keys = Array.from({ length: 7 }, (_, idx) => {
      const d = new Date(today);
      d.setDate(today.getDate() - (6 - idx));
      return d.toISOString().slice(0, 10);
    });
    const counts = new Map<string, number>();
    for (const item of mealRecords) {
      const key = isoDay(item.captured_at ?? item.created_at);
      if (!key) continue;
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    const max = Math.max(1, ...keys.map((key) => counts.get(key) ?? 0));
    return keys.map((key) => {
      const count = counts.get(key) ?? 0;
      return {
        key,
        count,
        height: Math.max(10, Math.round((count / max) * 64)),
        label: key.slice(5),
      };
    });
  }, [mealRecords]);

  const reminderBreakdown = useMemo(() => {
    let yes = 0;
    let no = 0;
    let unknown = 0;
    for (const reminder of reminders) {
      const confirmation = reminder.meal_confirmation;
      if (confirmation === "yes") yes += 1;
      else if (confirmation === "no") no += 1;
      else unknown += 1;
    }
    return { yes, no, unknown };
  }, [reminders]);

  const orderedAgentRecommendations = useMemo(() => {
    if (!agentFeed) return [];
    return (["breakfast", "lunch", "dinner", "snack"] as const)
      .map((slot) => agentFeed.recommendations[slot])
      .filter((item): item is NonNullable<typeof item> => Boolean(item));
  }, [agentFeed]);

  const orderedDailySuggestions = useMemo(() => {
    if (!dailySuggestions) return [];
    return (["breakfast", "lunch", "dinner", "snack"] as const)
      .map((slot) => dailySuggestions.bundle.suggestions[slot])
      .filter((item): item is NonNullable<typeof item> => Boolean(item));
  }, [dailySuggestions]);

  const dashboardError = status === "unauthenticated" ? "Sign in to use dashboard workflows." : null;

  useEffect(() => {
    if (status !== "authenticated") return;
    void loadPersonalization();
  }, [loadPersonalization, status]);

  return (
    <div>
      <PageTitle
        eyebrow="Overview"
        title="Daily Wellness Workspace"
        description="Unified operational dashboard for suggestions, household-aware reads, timeline inspection, and adherence trend monitoring."
        tags={["iteration target", "policy-ready", "live API"]}
      />

      {dashboardError ? <ErrorCard message={dashboardError} /> : null}

      <div className="mb-4 grid gap-4 xl:grid-cols-[1.1fr_1.3fr]">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Health Profile Personalization</CardTitle>
            <CardDescription>
              Persist the health, nutrition, and preference signals the agent uses to pace healthier daily recommendations.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-2">
                <Label htmlFor="profile-age">Age</Label>
                <Input id="profile-age" value={profileAge} onChange={(event) => setProfileAge(event.target.value)} placeholder="54" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="profile-locale">Locale</Label>
                <Input id="profile-locale" value={profileLocale} onChange={(event) => setProfileLocale(event.target.value)} placeholder="en-SG" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="profile-height-cm">Height (cm)</Label>
                <Input
                  id="profile-height-cm"
                  value={profileHeightCm}
                  onChange={(event) => setProfileHeightCm(event.target.value)}
                  placeholder="168"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="profile-weight-kg">Weight (kg)</Label>
                <Input
                  id="profile-weight-kg"
                  value={profileWeightKg}
                  onChange={(event) => setProfileWeightKg(event.target.value)}
                  placeholder="79"
                />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="profile-sodium-limit">Daily sodium limit (mg)</Label>
                <Input
                  id="profile-sodium-limit"
                  value={profileSodiumLimit}
                  onChange={(event) => setProfileSodiumLimit(event.target.value)}
                  placeholder="1500"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="profile-sugar-limit">Daily sugar limit (g)</Label>
                <Input
                  id="profile-sugar-limit"
                  value={profileSugarLimit}
                  onChange={(event) => setProfileSugarLimit(event.target.value)}
                  placeholder="24"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="profile-target-calories">Target calories / day</Label>
                <Input
                  id="profile-target-calories"
                  value={profileTargetCalories}
                  onChange={(event) => setProfileTargetCalories(event.target.value)}
                  placeholder="1850"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="profile-macro-focus">Macro focus</Label>
              <Input
                id="profile-macro-focus"
                value={profileMacroFocus}
                onChange={(event) => setProfileMacroFocus(event.target.value)}
                placeholder="higher_protein, lower_sugar"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="profile-goals">Nutrition goals</Label>
              <Input
                id="profile-goals"
                value={profileGoals}
                onChange={(event) => setProfileGoals(event.target.value)}
                placeholder="lower_sugar, heart_health"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="profile-cuisines">Preferred cuisines</Label>
              <Input
                id="profile-cuisines"
                value={profileCuisines}
                onChange={(event) => setProfileCuisines(event.target.value)}
                placeholder="teochew, local"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="profile-allergies">Allergies</Label>
                <Input
                  id="profile-allergies"
                  value={profileAllergies}
                  onChange={(event) => setProfileAllergies(event.target.value)}
                  placeholder="shellfish, peanuts"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="profile-dislikes">Disliked ingredients</Label>
                <Input
                  id="profile-dislikes"
                  value={profileDislikes}
                  onChange={(event) => setProfileDislikes(event.target.value)}
                  placeholder="lard, organ meat"
                />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="profile-conditions">Conditions</Label>
                <Input
                  id="profile-conditions"
                  value={profileConditions}
                  onChange={(event) => setProfileConditions(event.target.value)}
                  placeholder="Type 2 Diabetes:High"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="profile-medications">Medications</Label>
                <Input
                  id="profile-medications"
                  value={profileMedications}
                  onChange={(event) => setProfileMedications(event.target.value)}
                  placeholder="Metformin:500mg"
                />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-[180px_1fr_1fr] sm:items-end">
              <div className="space-y-2">
                <Label htmlFor="profile-budget">Budget</Label>
                <Select id="profile-budget" value={profileBudget} onChange={(event) => setProfileBudget(event.target.value as typeof profileBudget)}>
                  <option value="budget">Budget</option>
                  <option value="moderate">Moderate</option>
                  <option value="flexible">Flexible</option>
                </Select>
              </div>
              <Button disabled={status !== "authenticated" || profileBusy} onClick={saveHealthProfileDraft}>
                {profileBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Save Health Profile
              </Button>
              <Button
                variant="secondary"
                disabled={status !== "authenticated" || profileBusy || agentBusy}
                onClick={refreshAgentFeed}
              >
                {agentBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Refresh Agent Feed
              </Button>
            </div>
            {profileError ? <ErrorCard message={profileError} /> : null}
            {healthProfile ? (
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                <div className="metric-card">
                  <div className="section-kicker">Profile state</div>
                  <div className="mt-1 text-sm font-semibold">{healthProfile.completeness.state}</div>
                </div>
                <div className="metric-card">
                  <div className="section-kicker">BMI</div>
                  <div className="mt-1 text-sm font-semibold">{healthProfile.bmi == null ? "not enough data" : healthProfile.bmi.toFixed(1)}</div>
                </div>
                <div className="metric-card">
                  <div className="section-kicker">Macro focus</div>
                  <div className="mt-1 text-sm font-semibold">
                    {healthProfile.macro_focus.length ? healthProfile.macro_focus.join(", ") : "not set"}
                  </div>
                </div>
                <div className="metric-card">
                  <div className="section-kicker">Fallback mode</div>
                  <div className="mt-1 text-sm font-semibold">{healthProfile.fallback_mode ? "active" : "off"}</div>
                </div>
              </div>
            ) : null}
            {healthProfile ? (
              <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
                {healthProfile.completeness.missing_fields.length ? (
                  <>Missing structured context: {healthProfile.completeness.missing_fields.join(", ")}.</>
                ) : (
                  <>Profile is ready. The agent can optimize against your nutrition goals and logged behavior.</>
                )}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Adaptive Daily Meal Agent</CardTitle>
            <CardDescription>
              Behavior-aware daily recommendations that blend health constraints, learned meal preferences, timing patterns, and low-deviation healthier swaps.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {agentError ? <ErrorCard message={agentError} /> : null}
            {agentBusy && !agentFeed ? (
              <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
                Loading adaptive recommendation feed...
              </div>
            ) : null}
            {agentFeed ? (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge>{agentFeed.profile_state.completeness_state}</Badge>
                  <Badge variant="outline">Current slot: {agentFeed.temporal_context.current_slot}</Badge>
                  <Badge variant="outline">Fallback: {agentFeed.fallback_mode ? "warming up" : "off"}</Badge>
                  {agentFeed.profile_state.bmi != null ? <Badge variant="outline">BMI {agentFeed.profile_state.bmi.toFixed(1)}</Badge> : null}
                </div>
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="metric-card">
                    <div className="section-kicker">Meal history</div>
                    <div className="mt-1 text-sm font-semibold">{agentFeed.temporal_context.meal_history_count}</div>
                  </div>
                  <div className="metric-card">
                    <div className="section-kicker">Interaction count</div>
                    <div className="mt-1 text-sm font-semibold">{agentFeed.temporal_context.interaction_count}</div>
                  </div>
                  <div className="metric-card">
                    <div className="section-kicker">Target calories</div>
                    <div className="mt-1 text-sm font-semibold">
                      {agentFeed.profile_state.target_calories_per_day == null ? "profile default" : Math.round(agentFeed.profile_state.target_calories_per_day)}
                    </div>
                  </div>
                  <div className="metric-card">
                    <div className="section-kicker">Recent repeat guard</div>
                    <div className="mt-1 text-sm font-semibold">
                      {agentFeed.temporal_context.recent_repeat_titles.length
                        ? agentFeed.temporal_context.recent_repeat_titles.slice(0, 2).join(", ")
                        : "variety open"}
                    </div>
                  </div>
                </div>
                {agentFeed.fallback_mode ? (
                  <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
                    The agent is still warming up. It is using your profile plus deterministic ranking while it gathers enough accepted or dismissed interactions to personalize more aggressively.
                  </div>
                ) : null}
                {agentFeed.constraints_applied.length ? (
                  <div className="flex flex-wrap gap-2">
                    {agentFeed.constraints_applied.map((constraint) => (
                      <Badge key={constraint} variant="outline">
                        {constraint}
                      </Badge>
                    ))}
                  </div>
                ) : null}
                <div className="grid gap-3 xl:grid-cols-2">
                  {orderedAgentRecommendations.map((item) => (
                    <div key={`${item.slot}-${item.candidate_id}`} className="rounded-3xl border bg-background/40 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <div className="section-kicker">{item.slot}</div>
                          <div className="mt-1 text-lg font-semibold">{item.title}</div>
                          <div className="text-sm text-muted-foreground">{item.venue_type}</div>
                        </div>
                        <Badge variant={item.confidence >= 0.75 ? "default" : "outline"}>{formatPercent(item.confidence)} confidence</Badge>
                      </div>

                      <div className="mt-3 text-sm font-medium">Why the agent picked this</div>
                      <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
                        {item.why_it_fits.map((reason) => (
                          <li key={reason}>• {reason}</li>
                        ))}
                      </ul>

                      {item.caution_notes.length ? (
                        <>
                          <div className="mt-3 text-sm font-medium">Watch-outs</div>
                          <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
                            {item.caution_notes.map((note) => (
                              <li key={note}>• {note}</li>
                            ))}
                          </ul>
                        </>
                      ) : null}

                      <div className="mt-3 grid gap-2 sm:grid-cols-3">
                        <div className="metric-card">
                          <div className="section-kicker">Preference fit</div>
                          <div className="mt-1 text-sm font-semibold">{formatPercent(item.scores.preference_fit)}</div>
                        </div>
                        <div className="metric-card">
                          <div className="section-kicker">Adherence</div>
                          <div className="mt-1 text-sm font-semibold">{formatPercent(item.scores.adherence_likelihood)}</div>
                        </div>
                        <div className="metric-card">
                          <div className="section-kicker">Health gain</div>
                          <div className="mt-1 text-sm font-semibold">{formatPercent(item.scores.health_gain)}</div>
                        </div>
                      </div>

                      <div className="mt-3 grid gap-2 sm:grid-cols-3">
                        <div className="rounded-2xl border border-dashed p-3 text-sm text-muted-foreground">
                          Calories {formatSigned(item.health_gain_summary.calories, "kcal")}
                        </div>
                        <div className="rounded-2xl border border-dashed p-3 text-sm text-muted-foreground">
                          Sugar {formatSigned(item.health_gain_summary.sugar_g, "g")}
                        </div>
                        <div className="rounded-2xl border border-dashed p-3 text-sm text-muted-foreground">
                          Sodium {formatSigned(item.health_gain_summary.sodium_mg, "mg")}
                        </div>
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          disabled={agentActionId !== null}
                          onClick={() =>
                            submitRecommendationFeedback({
                              eventType: "accepted",
                              candidateId: item.candidate_id,
                              slot: item.slot,
                            })
                          }
                        >
                          {agentActionId === `accepted:${item.candidate_id}` ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                          Accept
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={agentActionId !== null}
                          onClick={() =>
                            submitRecommendationFeedback({
                              eventType: "dismissed",
                              candidateId: item.candidate_id,
                              slot: item.slot,
                            })
                          }
                        >
                          {agentActionId === `dismissed:${item.candidate_id}` ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                          Not for me
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={agentActionId !== null}
                          onClick={() =>
                            submitRecommendationFeedback({
                              eventType: "ignored",
                              candidateId: item.candidate_id,
                              slot: item.slot,
                            })
                          }
                        >
                          {agentActionId === `ignored:${item.candidate_id}` ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                          Skip
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>

                {agentFeed.substitutions ? (
                  <div className="rounded-3xl border bg-background/35 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="section-kicker">Healthier swap planner</div>
                        <div className="mt-1 text-lg font-semibold">{agentFeed.substitutions.source_meal.title}</div>
                        <div className="text-sm text-muted-foreground">{agentFeed.substitutions.source_meal.slot}</div>
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={agentActionId !== null}
                        onClick={() => refreshSubstitutions(agentFeed.substitutions!.source_meal.meal_id)}
                      >
                        {agentActionId === `refresh-substitutions:${agentFeed.substitutions.source_meal.meal_id}` ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : null}
                        Refresh swaps
                      </Button>
                    </div>
                    {agentFeed.substitutions.alternatives.length ? (
                      <div className="mt-3 grid gap-3 md:grid-cols-2">
                        {agentFeed.substitutions.alternatives.map((alternative) => (
                          <div key={alternative.candidate_id} className="rounded-2xl border border-dashed p-4">
                            <div className="text-sm font-semibold">{alternative.title}</div>
                            <div className="text-sm text-muted-foreground">{alternative.venue_type}</div>
                            <p className="mt-2 text-sm text-muted-foreground">{alternative.reasoning}</p>
                            <div className="mt-3 grid gap-2 sm:grid-cols-3">
                              <div className="metric-card">
                                <div className="section-kicker">Calories</div>
                                <div className="mt-1 text-sm font-semibold">{formatSigned(alternative.health_delta.calories, "kcal")}</div>
                              </div>
                              <div className="metric-card">
                                <div className="section-kicker">Sodium</div>
                                <div className="mt-1 text-sm font-semibold">{formatSigned(alternative.health_delta.sodium_mg, "mg")}</div>
                              </div>
                              <div className="metric-card">
                                <div className="section-kicker">Taste distance</div>
                                <div className="mt-1 text-sm font-semibold">{formatPercent(1 - alternative.taste_distance)}</div>
                              </div>
                            </div>
                            <div className="mt-3 flex flex-wrap items-center gap-2">
                              <Button
                                size="sm"
                                disabled={agentActionId !== null}
                                onClick={() =>
                                  submitRecommendationFeedback({
                                    eventType: "swap_selected",
                                    candidateId: alternative.candidate_id,
                                    slot: agentFeed.substitutions!.source_meal.slot,
                                    sourceMealId: agentFeed.substitutions!.source_meal.meal_id,
                                    selectedMealId: alternative.candidate_id,
                                  })
                                }
                              >
                                {agentActionId === `swap_selected:${alternative.candidate_id}` ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : null}
                                Use this swap
                              </Button>
                              <span className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                                {formatPercent(alternative.confidence)} confidence
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="mt-3 rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
                        {agentFeed.substitutions.blocked_reason ?? "No safer low-deviation swap is available for the selected meal yet."}
                      </div>
                    )}
                  </div>
                ) : null}

                {dailySuggestions ? (
                  <div className="rounded-3xl border bg-background/35 p-4">
                    <div className="section-kicker">Deterministic fallback guide</div>
                    <div className="mt-1 text-sm text-muted-foreground">
                      Structured baseline suggestions remain available while the adaptive ranker warms up or if learned preference state is sparse.
                    </div>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      {orderedDailySuggestions.map((item) => (
                        <div key={item.slot} className="rounded-2xl border border-dashed p-4">
                          <div className="section-kicker">{item.slot}</div>
                          <div className="mt-1 text-base font-semibold">{item.title}</div>
                          <div className="text-sm text-muted-foreground">{item.venue_type}</div>
                          <div className="mt-2 text-xs uppercase tracking-[0.24em] text-muted-foreground">
                            Confidence {formatPercent(item.confidence)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Suggestions Unified Flow</CardTitle>
            <CardDescription>Run report parse + recommendation generation in one action and inspect typed output.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Label htmlFor="dashboard-report-text">Report text</Label>
            <Textarea
              id="dashboard-report-text"
              value={reportText}
              onChange={(event) => setReportText(event.target.value)}
              placeholder="Paste biomarker report text here..."
              className="min-h-[140px]"
            />
            <Button disabled={status !== "authenticated" || suggestionBusy || !reportText.trim()} onClick={runUnifiedSuggestionFlow}>
              {suggestionBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Generate Suggestion
            </Button>
            {suggestionError ? <ErrorCard message={suggestionError} /> : null}
            {suggestionResult ? (
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="metric-card">
                  <div className="section-kicker">Safety Decision</div>
                  <div className="mt-1 text-sm font-semibold">{suggestionResult.suggestion.safety.decision}</div>
                </div>
                <div className="metric-card">
                  <div className="section-kicker">Suggestion ID</div>
                  <div className="mt-1 truncate text-sm font-semibold">{suggestionResult.suggestion.suggestion_id}</div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Household-Aware Data Views</CardTitle>
            <CardDescription>Load meals, reminders, and suggestions under `self` or `household` scope.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-[180px_1fr] sm:items-end">
              <div className="space-y-2">
                <Label htmlFor="dashboard-scope">Scope</Label>
                <Select id="dashboard-scope" value={scope} onChange={(event) => setScope(event.target.value as Scope)}>
                  <option value="self">Self</option>
                  <option value="household">Household</option>
                </Select>
              </div>
              <Button disabled={status !== "authenticated" || overviewBusy} onClick={loadHouseholdAwareViews}>
                {overviewBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Refresh Scope Data
              </Button>
            </div>
            {overviewError ? <ErrorCard message={overviewError} /> : null}
            <div className="grid gap-2 sm:grid-cols-3">
              <div className="metric-card">
                <div className="section-kicker">Meal Records</div>
                <div className="mt-1 text-lg font-semibold">{mealRecords.length}</div>
              </div>
              <div className="metric-card">
                <div className="section-kicker">Suggestions</div>
                <div className="mt-1 text-lg font-semibold">{suggestionItems.length}</div>
              </div>
              <div className="metric-card">
                <div className="section-kicker">Reminders</div>
                <div className="mt-1 text-lg font-semibold">{reminders.length}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 page-grid">
        <Card>
          <CardHeader>
            <CardTitle>Structured Timeline Viewers</CardTitle>
            <CardDescription>Inspect workflow timelines and alert outbox events using correlation and alert IDs.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Button disabled={status !== "authenticated" || workflowsBusy} onClick={loadWorkflowList}>
                {workflowsBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Load Workflows
              </Button>
              <Button variant="secondary" disabled={status !== "authenticated" || workflowsBusy || !selectedCorrelationId} onClick={loadSelectedWorkflow}>
                Open Selected Workflow
              </Button>
            </div>
            {workflowItems.length > 0 ? (
              <Select value={selectedCorrelationId} onChange={(event) => setSelectedCorrelationId(event.target.value)}>
                {workflowItems.map((item) => {
                  const correlationId = typeof item.correlation_id === "string" ? item.correlation_id : "";
                  const workflowName = typeof item.workflow_name === "string" ? item.workflow_name : "workflow";
                  if (!correlationId) return null;
                  return (
                    <option key={correlationId} value={correlationId}>
                      {workflowName} :: {correlationId}
                    </option>
                  );
                })}
              </Select>
            ) : null}
            {workflowsError ? <ErrorCard message={workflowsError} /> : null}
            {workflowDetail?.timeline_events ? (
              <div className="data-list">
                {workflowDetail.timeline_events.slice(0, 8).map((event, idx) => (
                  <div key={`${String(event.event_type)}-${idx}`} className="data-list-row">
                    <div className="text-sm font-semibold">{String(event.event_type ?? "event")}</div>
                    <div className="app-muted text-xs">{String(event.created_at ?? "")}</div>
                  </div>
                ))}
              </div>
            ) : null}

            <Separator />

            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
              <div className="space-y-2">
                <Label htmlFor="dashboard-alert-id">Alert ID</Label>
                <Input
                  id="dashboard-alert-id"
                  value={alertId}
                  onChange={(event) => setAlertId(event.target.value)}
                  placeholder="alert_..."
                />
              </div>
              <Button disabled={status !== "authenticated" || alertBusy || !alertId.trim()} onClick={loadAlertTimeline}>
                {alertBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Load Alert Timeline
              </Button>
            </div>
            {alertError ? <ErrorCard message={alertError} /> : null}
            {alertTimeline.length > 0 ? (
              <div className="data-list">
                {alertTimeline.slice(0, 6).map((event, idx) => (
                  <div key={`${String(event.state ?? event.event_type)}-${idx}`} className="data-list-row">
                    <div className="text-sm font-semibold">{String(event.state ?? event.event_type ?? "event")}</div>
                    <div className="app-muted text-xs">{String(event.created_at ?? "")}</div>
                  </div>
                ))}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Adherence and Confirmation Trends</CardTitle>
            <CardDescription>Simple operational charting from live reminders and meal capture data.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="metric-card">
              <div className="section-kicker">Meal Confirmation Rate</div>
              <div className="mt-1 text-2xl font-semibold">{Math.round(confirmationRate * 100)}%</div>
            </div>

            <div className="grid gap-2 sm:grid-cols-3">
              <div className="metric-card">
                <div className="section-kicker">Yes</div>
                <div className="mt-1 text-lg font-semibold">{reminderBreakdown.yes}</div>
              </div>
              <div className="metric-card">
                <div className="section-kicker">No</div>
                <div className="mt-1 text-lg font-semibold">{reminderBreakdown.no}</div>
              </div>
              <div className="metric-card">
                <div className="section-kicker">Unknown</div>
                <div className="mt-1 text-lg font-semibold">{reminderBreakdown.unknown}</div>
              </div>
            </div>

            <div className="metric-card">
              <div className="section-kicker mb-3">7-Day Meal Capture</div>
              <div className="flex items-end justify-between gap-2">
                {trendBars.map((bar) => (
                  <div key={bar.key} className="flex flex-1 flex-col items-center gap-1">
                    <div className="w-full rounded-md bg-[color:var(--accent)]/15">
                      <div
                        className="mx-auto rounded-md bg-[color:var(--accent)]"
                        style={{ height: `${bar.height}px`, width: "80%" }}
                      />
                    </div>
                    <div className="text-[11px] text-[color:var(--muted-foreground)]">{bar.label}</div>
                    <div className="text-xs font-medium">{bar.count}</div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          ["Meal Analysis", "Upload photos, inspect summaries, and review saved records.", "/meals"],
          ["Reminders", "Generate events and confirm meals with metrics feedback.", "/reminders"],
          ["Suggestions", "Parse report text and generate persisted suggestions.", "/suggestions"],
          ["Household", "Create a family-like group and manage invites/members.", "/household"],
        ].map(([title, text, href]) => (
          <Card key={title}>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{title}</CardTitle>
              <CardDescription>{text}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild size="sm" variant="secondary">
                <Link href={String(href)}>Open</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="mt-3 app-muted text-xs">Signed in as: {user ? `${user.display_name} (${user.account_role})` : "anonymous"}</div>
    </div>
  );
}
