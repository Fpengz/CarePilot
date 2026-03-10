"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LogOut } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { useSession } from "@/components/app/session-provider";
import { updateAuthProfile, logout } from "@/lib/api/auth-client";
import {
  getMobilityReminderSettings,
  updateMobilityReminderSettings,
} from "@/lib/api/reminder-client";
import {
  completeHealthProfileOnboarding,
  getHealthProfileOnboarding,
  updateHealthProfile,
  updateHealthProfileOnboarding,
} from "@/lib/api/profile-client";
import type {
  GuidedHealthStep,
  HealthProfile,
  HealthProfileOnboardingResponse,
  MobilityReminderSettings,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

import { HouseholdTab } from "./tabs/household-tab";
import { ClinicalSuggestionsTab } from "./tabs/clinical-suggestions-tab";

type SettingsTab = "account" | "health" | "reminders" | "household" | "clinical_suggestions";
type HealthViewMode = "guided" | "advanced";
type HealthProfileDraft = {
  age: string;
  locale: string;
  height_cm: string;
  weight_kg: string;
  daily_sodium_limit_mg: string;
  daily_sugar_limit_g: string;
  daily_protein_target_g: string;
  daily_fiber_target_g: string;
  target_calories_per_day: string;
  macro_focus: string;
  nutrition_goals: string;
  preferred_cuisines: string;
  allergies: string;
  disliked_ingredients: string;
  conditions: string;
  medications: string;
  budget_tier: "budget" | "moderate" | "flexible";
  preferred_notification_channel: string;
  meal_schedule: string;
};

const GUIDED_STEP_ORDER = [
  "basic_identity",
  "health_context",
  "nutrition_targets",
  "preferences",
  "review",
] as const;

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

function conditionsText(profile: HealthProfile): string {
  return profile.conditions.map((item) => `${item.name}:${item.severity}`).join(", ");
}

function medicationsText(profile: HealthProfile): string {
  return profile.medications.map((item) => `${item.name}:${item.dosage}`).join(", ");
}

function buildDraft(profile: HealthProfile): HealthProfileDraft {
  return {
    age: numberDraft(profile.age),
    locale: profile.locale || "en-SG",
    height_cm: numberDraft(profile.height_cm),
    weight_kg: numberDraft(profile.weight_kg),
    daily_sodium_limit_mg: String(profile.daily_sodium_limit_mg),
    daily_sugar_limit_g: String(profile.daily_sugar_limit_g),
    daily_protein_target_g: String(profile.daily_protein_target_g),
    daily_fiber_target_g: String(profile.daily_fiber_target_g),
    target_calories_per_day: numberDraft(profile.target_calories_per_day),
    macro_focus: profile.macro_focus.join(", "),
    nutrition_goals: profile.nutrition_goals.join(", "),
    preferred_cuisines: profile.preferred_cuisines.join(", "),
    allergies: profile.allergies.join(", "),
    disliked_ingredients: profile.disliked_ingredients.join(", "),
    conditions: conditionsText(profile),
    medications: medicationsText(profile),
    budget_tier: profile.budget_tier,
    preferred_notification_channel: profile.preferred_notification_channel || "in_app",
    meal_schedule: (profile.meal_schedule || [])
      .map((w) => `${w.slot}:${w.start_time}-${w.end_time}`)
      .join(", "),
  };
}

function buildFullProfilePayload(draft: HealthProfileDraft) {
  return {
    age: toOptionalNumber(draft.age),
    locale: draft.locale.trim(),
    height_cm: toOptionalNumber(draft.height_cm),
    weight_kg: toOptionalNumber(draft.weight_kg),
    daily_sodium_limit_mg: toOptionalNumber(draft.daily_sodium_limit_mg) ?? undefined,
    daily_sugar_limit_g: toOptionalNumber(draft.daily_sugar_limit_g) ?? undefined,
    daily_protein_target_g: toOptionalNumber(draft.daily_protein_target_g) ?? undefined,
    daily_fiber_target_g: toOptionalNumber(draft.daily_fiber_target_g) ?? undefined,
    target_calories_per_day: toOptionalNumber(draft.target_calories_per_day),
    macro_focus: csvToList(draft.macro_focus),
    nutrition_goals: csvToList(draft.nutrition_goals),
    preferred_cuisines: csvToList(draft.preferred_cuisines),
    allergies: csvToList(draft.allergies),
    disliked_ingredients: csvToList(draft.disliked_ingredients),
    conditions: csvToList(draft.conditions).map((item) => {
      const [name, severity = "Medium"] = item.split(":").map((part) => part.trim());
      return { name, severity };
    }),
    medications: csvToList(draft.medications).map((item) => {
      const [name, dosage = "unspecified"] = item.split(":").map((part) => part.trim());
      return { name, dosage, contraindications: [] };
    }),
    budget_tier: draft.budget_tier,
    preferred_notification_channel: draft.preferred_notification_channel,
    meal_schedule: csvToList(draft.meal_schedule).map((item) => {
      const [slot, range] = item.split(":").map((part) => part.trim());
      const [start_time, end_time] = (range || "00:00-00:00")
        .split("-")
        .map((part) => part.trim());
      return { slot, start_time, end_time, timezone: "Asia/Singapore" };
    }),
  };
}

function buildGuidedStepPayload(stepId: string, draft: HealthProfileDraft) {
  if (stepId === "basic_identity") {
    return {
      age: toOptionalNumber(draft.age),
      locale: draft.locale.trim(),
      height_cm: toOptionalNumber(draft.height_cm),
      weight_kg: toOptionalNumber(draft.weight_kg),
    };
  }
  if (stepId === "health_context") {
    return {
      conditions: csvToList(draft.conditions).map((item) => {
        const [name, severity = "Medium"] = item.split(":").map((part) => part.trim());
        return { name, severity };
      }),
      medications: csvToList(draft.medications).map((item) => {
        const [name, dosage = "unspecified"] = item.split(":").map((part) => part.trim());
        return { name, dosage, contraindications: [] };
      }),
    };
  }
  if (stepId === "nutrition_targets") {
    return {
      daily_sodium_limit_mg: toOptionalNumber(draft.daily_sodium_limit_mg) ?? undefined,
      daily_sugar_limit_g: toOptionalNumber(draft.daily_sugar_limit_g) ?? undefined,
      daily_protein_target_g: toOptionalNumber(draft.daily_protein_target_g) ?? undefined,
      daily_fiber_target_g: toOptionalNumber(draft.daily_fiber_target_g) ?? undefined,
      target_calories_per_day: toOptionalNumber(draft.target_calories_per_day),
      macro_focus: csvToList(draft.macro_focus),
      nutrition_goals: csvToList(draft.nutrition_goals),
    };
  }
  if (stepId === "preferences") {
    return {
      preferred_cuisines: csvToList(draft.preferred_cuisines),
      allergies: csvToList(draft.allergies),
      disliked_ingredients: csvToList(draft.disliked_ingredients),
      budget_tier: draft.budget_tier,
    };
  }
  return {};
}

function stepIndex(stepId: string): number {
  const index = GUIDED_STEP_ORDER.indexOf(stepId as (typeof GUIDED_STEP_ORDER)[number]);
  return index >= 0 ? index : 0;
}

function stepButtonVariant(currentStepId: string, activeStepId: string): "default" | "secondary" {
  if (currentStepId === activeStepId) return "default";
  return "secondary";
}

export function SettingsWorkspace() {
  const router = useRouter();
  const { status, user, refreshSession } = useSession();
  const [activeTab, setActiveTab] = useState<SettingsTab>("account");
  const [healthViewMode, setHealthViewMode] = useState<HealthViewMode>("guided");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [displayNameInput, setDisplayNameInput] = useState("");
  const [profileModeInput, setProfileModeInput] = useState<"self" | "caregiver">("self");
  const [savingAccount, setSavingAccount] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const [profileBusy, setProfileBusy] = useState(false);
  const [draft, setDraft] = useState<HealthProfileDraft>({
    age: "",
    locale: "en-SG",
    height_cm: "",
    weight_kg: "",
    daily_sodium_limit_mg: "1800",
    daily_sugar_limit_g: "30",
    daily_protein_target_g: "60",
    daily_fiber_target_g: "25",
    target_calories_per_day: "",
    macro_focus: "",
    nutrition_goals: "",
    preferred_cuisines: "",
    allergies: "",
    disliked_ingredients: "",
    conditions: "",
    medications: "",
    budget_tier: "moderate",
    preferred_notification_channel: "in_app",
    meal_schedule: "breakfast:07:00-09:00, lunch:12:00-14:00, dinner:18:00-20:00",
  });
  const [guidedSteps, setGuidedSteps] = useState<GuidedHealthStep[]>([]);
  const [guidedCurrentStep, setGuidedCurrentStep] = useState("basic_identity");
  const [guidedCompletedSteps, setGuidedCompletedSteps] = useState<string[]>([]);
  const [guidedComplete, setGuidedComplete] = useState(false);

  const [mobilitySettings, setMobilitySettings] = useState<MobilityReminderSettings>({
    enabled: false,
    interval_minutes: 120,
    active_start_time: "08:00",
    active_end_time: "20:00",
  });
  const [savingMobility, setSavingMobility] = useState(false);

  useEffect(() => {
    if (!user) return;
    setDisplayNameInput(user.display_name);
    setProfileModeInput(user.profile_mode);
  }, [user]);

  function applyOnboardingResponse(response: HealthProfileOnboardingResponse) {
    setDraft(buildDraft(response.profile));
    setGuidedSteps(response.steps);
    setGuidedCurrentStep(response.onboarding.current_step);
    setGuidedCompletedSteps(response.onboarding.completed_steps);
    setGuidedComplete(response.onboarding.is_complete);
  }

  useEffect(() => {
    if (status !== "authenticated") return;
    let cancelled = false;
    async function load() {
      setProfileBusy(true);
      setError(null);
      try {
        const [onboardingResponse, mobilityResponse] = await Promise.all([
          getHealthProfileOnboarding(),
          getMobilityReminderSettings(),
        ]);
        if (cancelled) return;
        applyOnboardingResponse(onboardingResponse);
        setMobilitySettings(mobilityResponse.settings);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setProfileBusy(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [status]);

  const activeGuidedStepId = guidedCurrentStep;
  const activeGuidedStep = guidedSteps.find((step) => step.id === activeGuidedStepId) ?? null;
  const activeStepIndex = stepIndex(activeGuidedStepId);

  async function handleAccountSave() {
    setSavingAccount(true);
    setError(null);
    setNotice(null);
    try {
      await updateAuthProfile({
        display_name: displayNameInput,
        profile_mode: profileModeInput,
      });
      await refreshSession();
      setNotice("Account settings updated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingAccount(false);
    }
  }

  async function handleLogout() {
    setLoggingOut(true);
    setError(null);
    try {
      await logout();
      router.replace("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setLoggingOut(false);
    }
  }

  async function handleHealthProfileSave() {
    setProfileBusy(true);
    setError(null);
    setNotice(null);
    try {
      await updateHealthProfile(buildFullProfilePayload(draft));
      const onboardingResponse = await getHealthProfileOnboarding();
      applyOnboardingResponse(onboardingResponse);
      setNotice("Advanced health profile saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setProfileBusy(false);
    }
  }

  async function handleGuidedNext() {
    if (!activeGuidedStepId) return;
    setProfileBusy(true);
    setError(null);
    setNotice(null);
    try {
      const response =
        activeGuidedStepId === "review"
          ? await completeHealthProfileOnboarding()
          : await updateHealthProfileOnboarding({
              step_id: activeGuidedStepId,
              profile: buildGuidedStepPayload(activeGuidedStepId, draft),
            });
      applyOnboardingResponse(response);
      setNotice(
        activeGuidedStepId === "review" ? "Guided setup completed." : "Step saved. Continue when ready.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setProfileBusy(false);
    }
  }

  function handleGuidedBack() {
    if (activeStepIndex === 0) return;
    setGuidedCurrentStep(GUIDED_STEP_ORDER[activeStepIndex - 1]);
  }

  async function handleMobilitySave() {
    setSavingMobility(true);
    setError(null);
    setNotice(null);
    try {
      const response = await updateMobilityReminderSettings(mobilitySettings);
      setMobilitySettings(response.settings);
      setNotice("Mobility reminder settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingMobility(false);
    }
  }

  return (
    <div>
      <PageTitle
        eyebrow="Account"
        title="Settings"
        description="Manage account preferences, guided profile setup, and reminder defaults without crowding the dashboard."

      />

      {error ? <ErrorCard message={error} /> : null}
      {notice ? (
        <Card className="mb-4 border-emerald-300/70 bg-emerald-50/70 dark:border-emerald-900/60 dark:bg-emerald-950/20">
          <CardContent className="py-4 text-sm">{notice}</CardContent>
        </Card>
      ) : null}

      <div className="mb-4 flex flex-wrap gap-2">
        <Button variant={activeTab === "account" ? "default" : "secondary"} onClick={() => setActiveTab("account")}>
          Identity
        </Button>
        <Button variant={activeTab === "health" ? "default" : "secondary"} onClick={() => setActiveTab("health")}>
          Health Profile
        </Button>
        <Button variant={activeTab === "reminders" ? "default" : "secondary"} onClick={() => setActiveTab("reminders")}>
          Reminder Settings
        </Button>
        <Button variant={activeTab === "household" ? "default" : "secondary"} onClick={() => setActiveTab("household")}>
          Household
        </Button>
        <Button variant={activeTab === "clinical_suggestions" ? "default" : "secondary"} onClick={() => setActiveTab("clinical_suggestions")}>
          Clinical Suggestions
        </Button>
      </div>

      {activeTab === "account" ? (
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Account Settings</CardTitle>
            <CardDescription>Keep your basic account context here. Password and session controls remain in the account drawer.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="settings-display-name">Display name</Label>
                <Input
                  id="settings-display-name"
                  value={displayNameInput}
                  onChange={(event) => setDisplayNameInput(event.target.value)}
                  disabled={status !== "authenticated"}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="settings-profile-mode">Usage mode</Label>
                <Select
                  id="settings-profile-mode"
                  value={profileModeInput}
                  onChange={(event) => setProfileModeInput(event.target.value as "self" | "caregiver")}
                  disabled={status !== "authenticated"}
                >
                  <option value="self">For yourself</option>
                  <option value="caregiver">Helping someone else</option>
                </Select>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={handleAccountSave} disabled={status !== "authenticated" || savingAccount}>
                <AsyncLabel active={savingAccount} idle="Save Account" loading="Saving" />
              </Button>
              <Button variant="ghost" className="text-destructive hover:text-destructive" onClick={handleLogout} disabled={loggingOut}>
                <LogOut className="mr-2 h-4 w-4" />
                <AsyncLabel active={loggingOut} idle="Sign Out" loading="Signing out" />
              </Button>
              <Button asChild variant="secondary">
                <Link href="/dashboard">Back to Dashboard</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {activeTab === "health" ? (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Health Profile Workspace</CardTitle>
              <CardDescription>
                Guided setup is the default path. Advanced edit stays available for fast bulk changes.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-sm">
                <div className="font-medium">
                  {guidedComplete
                    ? "Guided setup complete"
                    : `${guidedCompletedSteps.length} of ${guidedSteps.length || 5} steps completed`}
                </div>
                <div className="app-muted">
                  {guidedComplete
                    ? "You can revisit any step or use advanced edit for direct changes."
                    : "Progress autosaves one step at a time."}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={healthViewMode === "guided" ? "default" : "secondary"}
                  onClick={() => setHealthViewMode("guided")}
                >
                  Guided Setup
                </Button>
                <Button
                  variant={healthViewMode === "advanced" ? "default" : "secondary"}
                  onClick={() => setHealthViewMode("advanced")}
                >
                  Advanced Edit
                </Button>
              </div>
            </CardContent>
          </Card>

          {healthViewMode === "guided" ? (
            <Card className="grain-overlay">
              <CardHeader>
                <CardTitle>Guided Health Setup</CardTitle>
                <CardDescription>
                  {activeGuidedStep?.description ?? "Complete one structured step at a time."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-sm font-medium">Step {activeStepIndex + 1} of {guidedSteps.length || 5}</div>
                <div className="flex flex-wrap gap-2">
                  {guidedSteps.map((step) => (
                    <Button
                      key={step.id}
                      variant={stepButtonVariant(step.id, activeGuidedStepId)}
                      onClick={() => setGuidedCurrentStep(step.id)}
                    >
                      {step.title}
                    </Button>
                  ))}
                </div>

                {activeGuidedStepId === "basic_identity" ? (
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="space-y-2">
                      <Label htmlFor="guided-age">Age</Label>
                      <Input
                        id="guided-age"
                        value={draft.age}
                        onChange={(event) => setDraft((current) => ({ ...current, age: event.target.value }))}
                        placeholder="54"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="guided-locale">Locale</Label>
                      <Input
                        id="guided-locale"
                        value={draft.locale}
                        onChange={(event) => setDraft((current) => ({ ...current, locale: event.target.value }))}
                        placeholder="en-SG"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="guided-height">Height (cm)</Label>
                      <Input
                        id="guided-height"
                        value={draft.height_cm}
                        onChange={(event) => setDraft((current) => ({ ...current, height_cm: event.target.value }))}
                        placeholder="168"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="guided-weight">Weight (kg)</Label>
                      <Input
                        id="guided-weight"
                        value={draft.weight_kg}
                        onChange={(event) => setDraft((current) => ({ ...current, weight_kg: event.target.value }))}
                        placeholder="72"
                      />
                    </div>
                  </div>
                ) : null}

                {activeGuidedStepId === "health_context" ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="guided-conditions">Conditions</Label>
                      <Textarea
                        id="guided-conditions"
                        value={draft.conditions}
                        onChange={(event) => setDraft((current) => ({ ...current, conditions: event.target.value }))}
                        rows={4}
                        placeholder="Type 2 Diabetes:High"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="guided-medications">Medications</Label>
                      <Textarea
                        id="guided-medications"
                        value={draft.medications}
                        onChange={(event) => setDraft((current) => ({ ...current, medications: event.target.value }))}
                        rows={4}
                        placeholder="Metformin:500mg"
                      />
                    </div>
                  </div>
                ) : null}

                {activeGuidedStepId === "nutrition_targets" ? (
                  <div className="space-y-3">
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                      <div className="space-y-2">
                        <Label htmlFor="guided-sodium">Daily sodium limit (mg)</Label>
                        <Input
                          id="guided-sodium"
                          value={draft.daily_sodium_limit_mg}
                          onChange={(event) =>
                            setDraft((current) => ({ ...current, daily_sodium_limit_mg: event.target.value }))
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="guided-sugar">Daily sugar limit (g)</Label>
                        <Input
                          id="guided-sugar"
                          value={draft.daily_sugar_limit_g}
                          onChange={(event) =>
                            setDraft((current) => ({ ...current, daily_sugar_limit_g: event.target.value }))
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="guided-protein">Daily protein target (g)</Label>
                        <Input
                          id="guided-protein"
                          value={draft.daily_protein_target_g}
                          onChange={(event) =>
                            setDraft((current) => ({ ...current, daily_protein_target_g: event.target.value }))
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="guided-fiber">Daily fiber target (g)</Label>
                        <Input
                          id="guided-fiber"
                          value={draft.daily_fiber_target_g}
                          onChange={(event) =>
                            setDraft((current) => ({ ...current, daily_fiber_target_g: event.target.value }))
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="guided-calories">Target calories / day</Label>
                        <Input
                          id="guided-calories"
                          value={draft.target_calories_per_day}
                          onChange={(event) =>
                            setDraft((current) => ({ ...current, target_calories_per_day: event.target.value }))
                          }
                        />
                      </div>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="guided-macro-focus">Macro focus</Label>
                        <Input
                          id="guided-macro-focus"
                          value={draft.macro_focus}
                          onChange={(event) => setDraft((current) => ({ ...current, macro_focus: event.target.value }))}
                          placeholder="higher_protein, lower_sugar"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="guided-goals">Nutrition goals</Label>
                        <Input
                          id="guided-goals"
                          value={draft.nutrition_goals}
                          onChange={(event) =>
                            setDraft((current) => ({ ...current, nutrition_goals: event.target.value }))
                          }
                          placeholder="lower_sugar, heart_health"
                        />
                      </div>
                    </div>
                  </div>
                ) : null}

                {activeGuidedStepId === "preferences" ? (
                  <div className="space-y-3">
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="guided-cuisines">Preferred cuisines</Label>
                        <Input
                          id="guided-cuisines"
                          value={draft.preferred_cuisines}
                          onChange={(event) =>
                            setDraft((current) => ({ ...current, preferred_cuisines: event.target.value }))
                          }
                          placeholder="teochew, local"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="guided-budget">Budget</Label>
                        <Select
                          id="guided-budget"
                          value={draft.budget_tier}
                          onChange={(event) =>
                            setDraft((current) => ({
                              ...current,
                              budget_tier: event.target.value as HealthProfileDraft["budget_tier"],
                            }))
                          }
                        >
                          <option value="budget">Budget</option>
                          <option value="moderate">Moderate</option>
                          <option value="flexible">Flexible</option>
                        </Select>
                      </div>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="guided-allergies">Allergies</Label>
                        <Input
                          id="guided-allergies"
                          value={draft.allergies}
                          onChange={(event) => setDraft((current) => ({ ...current, allergies: event.target.value }))}
                          placeholder="shellfish, peanuts"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="guided-dislikes">Disliked ingredients</Label>
                        <Input
                          id="guided-dislikes"
                          value={draft.disliked_ingredients}
                          onChange={(event) =>
                            setDraft((current) => ({ ...current, disliked_ingredients: event.target.value }))
                          }
                          placeholder="lard, organ meat"
                        />
                      </div>
                    </div>
                  </div>
                ) : null}

                {activeGuidedStepId === "review" ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Basics</div>
                      <div className="mt-1 text-sm font-medium">
                        {draft.age || "Age not set"} / {draft.locale || "Locale not set"}
                      </div>
                      <div className="app-muted mt-1 text-xs">
                        {draft.height_cm || "?"} cm / {draft.weight_kg || "?"} kg
                      </div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Targets</div>
                      <div className="mt-1 text-sm font-medium">
                        {draft.daily_protein_target_g}g protein / {draft.daily_fiber_target_g}g fiber
                      </div>
                      <div className="app-muted mt-1 text-xs">
                        {draft.daily_sodium_limit_mg}mg sodium / {draft.daily_sugar_limit_g}g sugar
                      </div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Health context</div>
                      <div className="mt-1 text-sm font-medium">{draft.conditions || "No conditions recorded"}</div>
                      <div className="app-muted mt-1 text-xs">{draft.medications || "No medications recorded"}</div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Preferences</div>
                      <div className="mt-1 text-sm font-medium">{draft.preferred_cuisines || "No cuisines recorded"}</div>
                      <div className="app-muted mt-1 text-xs">
                        {draft.allergies || "No allergies"} / {draft.budget_tier}
                      </div>
                    </div>
                  </div>
                ) : null}

                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    onClick={handleGuidedBack}
                    disabled={profileBusy || activeStepIndex === 0}
                  >
                    Back
                  </Button>
                  <Button onClick={handleGuidedNext} disabled={status !== "authenticated" || profileBusy}>
                    <AsyncLabel
                      active={profileBusy}
                      idle={activeGuidedStepId === "review" ? "Save and Finish" : "Save and Continue"}
                      loading="Saving"
                    />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : null}

          {healthViewMode === "advanced" ? (
            <Card className="grain-overlay">
              <CardHeader>
                <CardTitle>Advanced Health Profile</CardTitle>
                <CardDescription>Direct form editing for power users who want to update the entire profile at once.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="space-y-2">
                    <Label htmlFor="profile-age">Age</Label>
                    <Input id="profile-age" value={draft.age} onChange={(event) => setDraft((current) => ({ ...current, age: event.target.value }))} placeholder="54" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-locale">Locale</Label>
                    <Input id="profile-locale" value={draft.locale} onChange={(event) => setDraft((current) => ({ ...current, locale: event.target.value }))} placeholder="en-SG" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-height-cm">Height (cm)</Label>
                    <Input id="profile-height-cm" value={draft.height_cm} onChange={(event) => setDraft((current) => ({ ...current, height_cm: event.target.value }))} placeholder="168" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-weight-kg">Weight (kg)</Label>
                    <Input id="profile-weight-kg" value={draft.weight_kg} onChange={(event) => setDraft((current) => ({ ...current, weight_kg: event.target.value }))} placeholder="79" />
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                  <div className="space-y-2">
                    <Label htmlFor="profile-sodium-limit">Daily sodium limit (mg)</Label>
                    <Input id="profile-sodium-limit" value={draft.daily_sodium_limit_mg} onChange={(event) => setDraft((current) => ({ ...current, daily_sodium_limit_mg: event.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-sugar-limit">Daily sugar limit (g)</Label>
                    <Input id="profile-sugar-limit" value={draft.daily_sugar_limit_g} onChange={(event) => setDraft((current) => ({ ...current, daily_sugar_limit_g: event.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-protein-target">Daily protein target (g)</Label>
                    <Input id="profile-protein-target" value={draft.daily_protein_target_g} onChange={(event) => setDraft((current) => ({ ...current, daily_protein_target_g: event.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-fiber-target">Daily fiber target (g)</Label>
                    <Input id="profile-fiber-target" value={draft.daily_fiber_target_g} onChange={(event) => setDraft((current) => ({ ...current, daily_fiber_target_g: event.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-target-calories">Target calories / day</Label>
                    <Input id="profile-target-calories" value={draft.target_calories_per_day} onChange={(event) => setDraft((current) => ({ ...current, target_calories_per_day: event.target.value }))} />
                  </div>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="profile-macro-focus">Macro focus</Label>
                    <Input id="profile-macro-focus" value={draft.macro_focus} onChange={(event) => setDraft((current) => ({ ...current, macro_focus: event.target.value }))} placeholder="higher_protein, lower_sugar" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-goals">Nutrition goals</Label>
                    <Input id="profile-goals" value={draft.nutrition_goals} onChange={(event) => setDraft((current) => ({ ...current, nutrition_goals: event.target.value }))} placeholder="lower_sugar, heart_health" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-cuisines">Preferred cuisines</Label>
                    <Input id="profile-cuisines" value={draft.preferred_cuisines} onChange={(event) => setDraft((current) => ({ ...current, preferred_cuisines: event.target.value }))} placeholder="teochew, local" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-budget">Budget</Label>
                    <Select id="profile-budget" value={draft.budget_tier} onChange={(event) => setDraft((current) => ({ ...current, budget_tier: event.target.value as HealthProfileDraft["budget_tier"] }))}>
                      <option value="budget">Budget</option>
                      <option value="moderate">Moderate</option>
                      <option value="flexible">Flexible</option>
                    </Select>
                  </div>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="profile-allergies">Allergies</Label>
                    <Input id="profile-allergies" value={draft.allergies} onChange={(event) => setDraft((current) => ({ ...current, allergies: event.target.value }))} placeholder="shellfish, peanuts" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-dislikes">Disliked ingredients</Label>
                    <Input id="profile-dislikes" value={draft.disliked_ingredients} onChange={(event) => setDraft((current) => ({ ...current, disliked_ingredients: event.target.value }))} placeholder="lard, organ meat" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-notification-channel">Preferred notification channel</Label>
                    <Select id="profile-notification-channel" value={draft.preferred_notification_channel} onChange={(event) => setDraft((current) => ({ ...current, preferred_notification_channel: event.target.value }))}>
                      <option value="in_app">In-App</option>
                      <option value="push">Push Notification</option>
                      <option value="email">Email</option>
                      <option value="sms">SMS</option>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-meal-schedule">Meal schedule (slot:HH:MM-HH:MM)</Label>
                    <Input id="profile-meal-schedule" value={draft.meal_schedule} onChange={(event) => setDraft((current) => ({ ...current, meal_schedule: event.target.value }))} placeholder="breakfast:07:00-09:00, lunch:12:00-14:00" />
                  </div>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="profile-conditions">Conditions</Label>
                    <Textarea id="profile-conditions" value={draft.conditions} onChange={(event) => setDraft((current) => ({ ...current, conditions: event.target.value }))} rows={4} placeholder="Type 2 Diabetes:High" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-medications">Medications</Label>
                    <Textarea id="profile-medications" value={draft.medications} onChange={(event) => setDraft((current) => ({ ...current, medications: event.target.value }))} rows={4} placeholder="Metformin:500mg" />
                  </div>
                </div>
                <Button onClick={handleHealthProfileSave} disabled={status !== "authenticated" || profileBusy}>
                  <AsyncLabel active={profileBusy} idle="Save Advanced Profile" loading="Saving" />
                </Button>
              </CardContent>
            </Card>
          ) : null}
        </div>
      ) : null}

      {activeTab === "reminders" ? (
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Reminder Settings</CardTitle>
            <CardDescription>Configure mobility reminders here. Delivery channels and reminder history stay on the Reminders page.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="mobility-enabled">Mobility reminders</Label>
                <Select
                  id="mobility-enabled"
                  value={mobilitySettings.enabled ? "enabled" : "disabled"}
                  onChange={(event) =>
                    setMobilitySettings((current) => ({
                      ...current,
                      enabled: event.target.value === "enabled",
                    }))
                  }
                >
                  <option value="disabled">Disabled</option>
                  <option value="enabled">Enabled</option>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="mobility-interval">Interval (minutes)</Label>
                <Input
                  id="mobility-interval"
                  value={String(mobilitySettings.interval_minutes)}
                  onChange={(event) =>
                    setMobilitySettings((current) => ({
                      ...current,
                      interval_minutes: Number(event.target.value) || current.interval_minutes,
                    }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="mobility-start">Active start time</Label>
                <Input
                  id="mobility-start"
                  value={mobilitySettings.active_start_time}
                  onChange={(event) =>
                    setMobilitySettings((current) => ({
                      ...current,
                      active_start_time: event.target.value,
                    }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="mobility-end">Active end time</Label>
                <Input
                  id="mobility-end"
                  value={mobilitySettings.active_end_time}
                  onChange={(event) =>
                    setMobilitySettings((current) => ({
                      ...current,
                      active_end_time: event.target.value,
                    }))
                  }
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={handleMobilitySave} disabled={status !== "authenticated" || savingMobility}>
                <AsyncLabel active={savingMobility} idle="Save Mobility Settings" loading="Saving" />
              </Button>
              <Button asChild variant="secondary">
                <Link href="/reminders">Open Reminders</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {activeTab === "household" ? <HouseholdTab /> : null}
      {activeTab === "clinical_suggestions" ? <ClinicalSuggestionsTab /> : null}
    </div>
  );
}
