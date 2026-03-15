"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useDeferredValue } from "react";
import { LogOut, User, Heart, Bell, Users, Lightbulb, Shield, ChevronRight } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { useSession } from "@/components/app/session-provider";
import { updateAuthProfile, logout } from "@/lib/api/auth-client";
import {
  getMobilityReminderSettings,
  listReminderNotificationEndpoints,
  listReminderNotificationPreferences,
  updateMobilityReminderSettings,
  updateReminderNotificationEndpoints,
  updateReminderNotificationPreferences,
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
  ReminderNotificationEndpoint,
  ReminderNotificationPreferenceRule,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

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
  const [savingDelivery, setSavingDelivery] = useState(false);
  const [preferences, setPreferences] = useState<ReminderNotificationPreferenceRule[]>([]);
  const [endpoints, setEndpoints] = useState<ReminderNotificationEndpoint[]>([]);
  const [emailDestination, setEmailDestination] = useState("");
  const [smsDestination, setSmsDestination] = useState("");
  const [emailVerified, setEmailVerified] = useState(true);
  const [smsVerified, setSmsVerified] = useState(false);
  const [inAppEnabled, setInAppEnabled] = useState(true);
  const [inAppOffset, setInAppOffset] = useState(0);
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [emailOffset, setEmailOffset] = useState(0);
  const [smsEnabled, setSmsEnabled] = useState(false);
  const [smsOffset, setSmsOffset] = useState(0);
  const [telegramEnabled, setTelegramEnabled] = useState(false);
  const [telegramOffset, setTelegramOffset] = useState(0);
  const [telegramDestination, setTelegramDestination] = useState("");
  const [telegramVerified, setTelegramVerified] = useState(true);

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
        const [onboardingResponse, mobilityResponse, preferenceResponse, endpointResponse] = await Promise.all([
          getHealthProfileOnboarding(),
          getMobilityReminderSettings(),
          listReminderNotificationPreferences(),
          listReminderNotificationEndpoints(),
        ]);
        if (cancelled) return;
        applyOnboardingResponse(onboardingResponse);
        setMobilitySettings(mobilityResponse.settings);
        setPreferences(preferenceResponse.preferences);
        setEndpoints(endpointResponse.endpoints);

        const inAppRule = preferenceResponse.preferences.find((item) => item.channel === "in_app");
        const emailRule = preferenceResponse.preferences.find((item) => item.channel === "email");
        const smsRule = preferenceResponse.preferences.find((item) => item.channel === "sms");
        const telegramRule = preferenceResponse.preferences.find((item) => item.channel === "telegram");
        setInAppEnabled(Boolean(inAppRule?.enabled ?? true));
        setInAppOffset(inAppRule?.offset_minutes ?? 0);
        setEmailEnabled(Boolean(emailRule?.enabled));
        setEmailOffset(emailRule?.offset_minutes ?? 0);
        setSmsEnabled(Boolean(smsRule?.enabled));
        setSmsOffset(smsRule?.offset_minutes ?? 0);
        setTelegramEnabled(Boolean(telegramRule?.enabled));
        setTelegramOffset(telegramRule?.offset_minutes ?? 0);

        const emailEndpoint = endpointResponse.endpoints.find((item) => item.channel === "email");
        const smsEndpoint = endpointResponse.endpoints.find((item) => item.channel === "sms");
        const telegramEndpoint = endpointResponse.endpoints.find((item) => item.channel === "telegram");
        setEmailDestination(emailEndpoint?.destination ?? "");
        setEmailVerified(Boolean(emailEndpoint?.verified ?? true));
        setSmsDestination(smsEndpoint?.destination ?? "");
        setSmsVerified(Boolean(smsEndpoint?.verified));
        setTelegramDestination(telegramEndpoint?.destination ?? "");
        setTelegramVerified(Boolean(telegramEndpoint?.verified ?? true));
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

  async function handleDeliverySave() {
    setSavingDelivery(true);
    setError(null);
    setNotice(null);
    try {
      const [nextPreferences, nextEndpoints] = await Promise.all([
        updateReminderNotificationPreferences({
          rules: [
            { channel: "in_app", offset_minutes: inAppOffset, enabled: inAppEnabled },
            { channel: "email", offset_minutes: emailOffset, enabled: emailEnabled },
            { channel: "sms", offset_minutes: smsOffset, enabled: smsEnabled },
            { channel: "telegram", offset_minutes: telegramOffset, enabled: telegramEnabled },
          ],
        }),
        updateReminderNotificationEndpoints({
          endpoints: [
            ...(emailDestination ? [{ channel: "email", destination: emailDestination, verified: emailVerified }] : []),
            ...(smsDestination ? [{ channel: "sms", destination: smsDestination, verified: smsVerified }] : []),
            ...(telegramDestination ? [{ channel: "telegram", destination: telegramDestination, verified: telegramVerified }] : []),
          ],
        }),
      ]);
      setPreferences(nextPreferences.preferences);
      setEndpoints(nextEndpoints.endpoints);
      setNotice("Delivery preferences saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingDelivery(false);
    }
  }

  return (
    <div className="section-stack">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Configuration</h1>
        <p className="text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl text-sm">
          Fine-tune your health profile, manage care circle members, and configure reminder delivery channels.
        </p>
      </div>

      {error && <ErrorCard message={error} />}
      {notice && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 animate-in fade-in slide-in-from-top-2">
          {notice}
        </div>
      )}

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as SettingsTab)} className="w-full space-y-8">
        <div className="border-b border-[color:var(--border-soft)]">
          <TabsList className="bg-transparent h-auto p-0 gap-8">
            <TabsTrigger value="account" className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-[color:var(--accent)] data-[state=active]:text-[color:var(--foreground)] shadow-none">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4" />
                <span>Identity</span>
              </div>
            </TabsTrigger>
            <TabsTrigger value="health" className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-[color:var(--accent)] data-[state=active]:text-[color:var(--foreground)] shadow-none">
              <div className="flex items-center gap-2">
                <Heart className="h-4 w-4" />
                <span>Health Profile</span>
              </div>
            </TabsTrigger>
            <TabsTrigger value="reminders" className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-[color:var(--accent)] data-[state=active]:text-[color:var(--foreground)] shadow-none">
              <div className="flex items-center gap-2">
                <Bell className="h-4 w-4" />
                <span>Delivery</span>
              </div>
            </TabsTrigger>
            <TabsTrigger value="household" className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-[color:var(--accent)] data-[state=active]:text-[color:var(--foreground)] shadow-none">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                <span>Household</span>
              </div>
            </TabsTrigger>
            <TabsTrigger value="clinical_suggestions" className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-[color:var(--accent)] data-[state=active]:text-[color:var(--foreground)] shadow-none">
              <div className="flex items-center gap-2">
                <Lightbulb className="h-4 w-4" />
                <span>Suggestions</span>
              </div>
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="account" className="mt-0 focus-visible:outline-none">
          <div className="page-grid items-start">
            <div className="clinical-card space-y-8">
              <div className="space-y-1">
                <h3 className="clinical-subtitle">Account Context</h3>
                <p className="clinical-body">Basic identity and usage mode for the application.</p>
              </div>
              <div className="grid gap-6">
                <div className="space-y-2">
                  <Label htmlFor="settings-display-name">Display Name</Label>
                  <Input
                    id="settings-display-name"
                    value={displayNameInput}
                    onChange={(event) => setDisplayNameInput(event.target.value)}
                    disabled={status !== "authenticated"}
                    className="h-11 rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="settings-profile-mode">Clinical Role</Label>
                  <Select
                    id="settings-profile-mode"
                    value={profileModeInput}
                    onChange={(event) => setProfileModeInput(event.target.value as "self" | "caregiver")}
                    disabled={status !== "authenticated"}
                  >
                    <option value="self">Managing for myself</option>
                    <option value="caregiver">Caregiver role (Managing for someone else)</option>
                  </Select>
                </div>
                <div className="pt-4 border-t border-[color:var(--border-soft)] flex flex-wrap gap-3">
                  <Button onClick={handleAccountSave} disabled={status !== "authenticated" || savingAccount} className="h-11 px-8 rounded-xl shadow-sm">
                    <AsyncLabel active={savingAccount} idle="Update Account" loading="Saving" />
                  </Button>
                  <Button variant="ghost" className="h-11 px-6 rounded-xl text-rose-600 hover:text-rose-700 hover:bg-rose-50" onClick={handleLogout} disabled={loggingOut}>
                    <LogOut className="mr-2 h-4 w-4" />
                    <AsyncLabel active={loggingOut} idle="Sign Out" loading="Signing out" />
                  </Button>
                </div>
              </div>
            </div>

            <div className="space-y-8">
              <div className="clinical-card bg-[color:var(--accent)]/5 border-[color:var(--accent)]/10">
                <div className="flex items-center gap-2 text-[color:var(--accent)] mb-4">
                  <Shield className="h-4 w-4" />
                  <span className="text-[10px] font-bold uppercase tracking-widest">Privacy & Security</span>
                </div>
                <p className="text-xs leading-relaxed text-[color:var(--muted-foreground)]">
                  Your data is encrypted at rest and in transit. We prioritize clinical privacy and patient autonomy in all assistant interactions.
                </p>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="health" className="mt-0 focus-visible:outline-none">
          <div className="section-stack">
            <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-6">
              <div className="space-y-1">
                <div className="text-sm font-bold">{guidedComplete ? "Health setup complete" : "Continue guided setup"}</div>
                <div className="text-xs text-[color:var(--muted-foreground)]">
                  {guidedCompletedSteps.length} of {guidedSteps.length || 5} clinical benchmarks established.
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant={healthViewMode === "guided" ? "default" : "secondary"} size="sm" onClick={() => setHealthViewMode("guided")} className="rounded-lg">Guided</Button>
                <Button variant={healthViewMode === "advanced" ? "default" : "secondary"} size="sm" onClick={() => setHealthViewMode("advanced")} className="rounded-lg">Advanced</Button>
              </div>
            </div>

            {healthViewMode === "guided" ? (
              <div className="clinical-card space-y-8 animate-in fade-in slide-in-from-bottom-2">
                <div className="space-y-1">
                  <h3 className="clinical-subtitle">{activeGuidedStep?.title ?? "Guided Setup"}</h3>
                  <p className="clinical-body">{activeGuidedStep?.description ?? "Establishing your clinical baseline."}</p>
                </div>

                <div className="grid gap-8">
                  {activeGuidedStepId === "basic_identity" && (
                    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                      <div className="space-y-2">
                        <Label htmlFor="guided-age">Age</Label>
                        <Input id="guided-age" value={draft.age} onChange={(e) => setDraft(d => ({ ...d, age: e.target.value }))} className="h-11 rounded-xl" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="guided-height">Height (cm)</Label>
                        <Input id="guided-height" value={draft.height_cm} onChange={(e) => setDraft(d => ({ ...d, height_cm: e.target.value }))} className="h-11 rounded-xl" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="guided-weight">Weight (kg)</Label>
                        <Input id="guided-weight" value={draft.weight_kg} onChange={(e) => setDraft(d => ({ ...d, weight_kg: e.target.value }))} className="h-11 rounded-xl" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="guided-locale">Locale</Label>
                        <Input id="guided-locale" value={draft.locale} onChange={(e) => setDraft(d => ({ ...d, locale: e.target.value }))} className="h-11 rounded-xl" />
                      </div>
                    </div>
                  )}

                  {activeGuidedStepId === "health_context" && (
                    <div className="grid gap-6 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="guided-conditions">Conditions</Label>
                        <Textarea id="guided-conditions" value={draft.conditions} onChange={(e) => setDraft(d => ({ ...d, conditions: e.target.value }))} rows={4} placeholder="Type 2 Diabetes:High" className="rounded-xl" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="guided-medications">Medications</Label>
                        <Textarea id="guided-medications" value={draft.medications} onChange={(e) => setDraft(d => ({ ...d, medications: e.target.value }))} rows={4} placeholder="Metformin:500mg" className="rounded-xl" />
                      </div>
                    </div>
                  )}

                  {activeGuidedStepId === "nutrition_targets" && (
                    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                      <div className="space-y-2">
                        <Label htmlFor="guided-sodium">Sodium Limit (mg)</Label>
                        <Input id="guided-sodium" value={draft.daily_sodium_limit_mg} onChange={(e) => setDraft(d => ({ ...d, daily_sodium_limit_mg: e.target.value }))} className="h-11 rounded-xl" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="guided-sugar">Sugar Limit (g)</Label>
                        <Input id="guided-sugar" value={draft.daily_sugar_limit_g} onChange={(e) => setDraft(d => ({ ...d, daily_sugar_limit_g: e.target.value }))} className="h-11 rounded-xl" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="guided-calories">Calories Target</Label>
                        <Input id="guided-calories" value={draft.target_calories_per_day} onChange={(e) => setDraft(d => ({ ...d, target_calories_per_day: e.target.value }))} className="h-11 rounded-xl" />
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-6 border-t border-[color:var(--border-soft)]">
                    <Button variant="ghost" onClick={handleGuidedBack} disabled={profileBusy || activeStepIndex === 0} className="h-11 px-6 rounded-xl">Back</Button>
                    <Button onClick={handleGuidedNext} disabled={status !== "authenticated" || profileBusy} className="h-11 px-8 rounded-xl shadow-sm">
                      <AsyncLabel active={profileBusy} idle={activeGuidedStepId === "review" ? "Save and Finish" : "Continue"} loading="Saving" />
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="clinical-card space-y-8 animate-in fade-in slide-in-from-bottom-2">
                <div className="space-y-1">
                  <h3 className="clinical-subtitle">Clinical Profile</h3>
                  <p className="clinical-body">Direct management of nutritional limits and care parameters.</p>
                </div>
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                   {/* Compact advanced fields */}
                   <div className="space-y-2">
                    <Label>Sodium Limit (mg)</Label>
                    <Input value={draft.daily_sodium_limit_mg} onChange={(e) => setDraft(d => ({ ...d, daily_sodium_limit_mg: e.target.value }))} className="h-11 rounded-xl" />
                  </div>
                  <div className="space-y-2">
                    <Label>Sugar Limit (g)</Label>
                    <Input value={draft.daily_sugar_limit_g} onChange={(e) => setDraft(d => ({ ...d, daily_sugar_limit_g: e.target.value }))} className="h-11 rounded-xl" />
                  </div>
                  <div className="space-y-2">
                    <Label>Calories Target</Label>
                    <Input value={draft.target_calories_per_day} onChange={(e) => setDraft(d => ({ ...d, target_calories_per_day: e.target.value }))} className="h-11 rounded-xl" />
                  </div>
                </div>
                <Button onClick={handleHealthProfileSave} disabled={status !== "authenticated" || profileBusy} className="h-11 px-8 rounded-xl shadow-sm">
                  <AsyncLabel active={profileBusy} idle="Save Profile Changes" loading="Saving" />
                </Button>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="reminders" className="mt-0 focus-visible:outline-none">
          <div className="page-grid items-start">
            <div className="clinical-card space-y-8">
              <div className="space-y-1">
                <h3 className="clinical-subtitle">Notification Channels</h3>
                <p className="clinical-body">Configure how the assistant delivers timely care alerts.</p>
              </div>
              <div className="space-y-6">
                <div className="flex items-center justify-between p-4 rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)]">
                  <div className="space-y-0.5">
                    <Label className="text-sm font-bold">In-App Notifications</Label>
                    <p className="text-xs text-[color:var(--muted-foreground)]">Receive alerts while using the platform.</p>
                  </div>
                  <input type="checkbox" checked={inAppEnabled} onChange={(e) => setInAppEnabled(e.target.checked)} className="h-5 w-5 rounded border-gray-300 text-[color:var(--accent)] focus:ring-[color:var(--accent)]" />
                </div>
                <div className="flex items-center justify-between p-4 rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)]">
                  <div className="space-y-0.5">
                    <Label className="text-sm font-bold">Email Digest</Label>
                    <p className="text-xs text-[color:var(--muted-foreground)]">Morning summary of care tasks.</p>
                  </div>
                  <input type="checkbox" checked={emailEnabled} onChange={(e) => setEmailEnabled(e.target.checked)} className="h-5 w-5 rounded border-gray-300 text-[color:var(--accent)] focus:ring-[color:var(--accent)]" />
                </div>
                <div className="flex flex-col gap-4 p-4 rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)]">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="text-sm font-bold">Telegram Delivery</Label>
                      <p className="text-xs text-[color:var(--muted-foreground)]">Direct alerts via Telegram bot.</p>
                    </div>
                    <input type="checkbox" checked={telegramEnabled} onChange={(e) => setTelegramEnabled(e.target.checked)} className="h-5 w-5 rounded border-gray-300 text-[color:var(--accent)] focus:ring-[color:var(--accent)]" />
                  </div>
                  {telegramEnabled && (
                    <div className="space-y-2 animate-in fade-in slide-in-from-top-1">
                      <Label htmlFor="telegram-chat-id" className="text-[10px] uppercase font-bold tracking-widest opacity-60">Chat ID</Label>
                      <Input
                        id="telegram-chat-id"
                        placeholder="e.g. 123456789"
                        value={telegramDestination}
                        onChange={(e) => setTelegramDestination(e.target.value)}
                        className="h-10 rounded-lg text-xs"
                      />
                    </div>
                  )}
                </div>
                <Button onClick={handleDeliverySave} disabled={status !== "authenticated" || savingDelivery} className="h-11 w-full rounded-xl shadow-sm">
                  <AsyncLabel active={savingDelivery} idle="Save Delivery Rules" loading="Saving" />
                </Button>
              </div>
            </div>
            
            <div className="clinical-card space-y-8">
              <div className="space-y-1">
                <h3 className="clinical-subtitle">Mobility Alerts</h3>
                <p className="clinical-body">Timely prompts for stretching and physical movement.</p>
              </div>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Interval (Minutes)</Label>
                  <Input value={String(mobilitySettings.interval_minutes)} onChange={(e) => setMobilitySettings(s => ({ ...s, interval_minutes: Number(e.target.value) || 120 }))} className="h-11 rounded-xl" />
                </div>
                <Button onClick={handleMobilitySave} disabled={status !== "authenticated" || savingMobility} className="h-11 w-full rounded-xl shadow-sm">
                  <AsyncLabel active={savingMobility} idle="Save Mobility Settings" loading="Saving" />
                </Button>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="household" className="mt-0 focus-visible:outline-none">
          <HouseholdTab />
        </TabsContent>

        <TabsContent value="clinical_suggestions" className="mt-0 focus-visible:outline-none">
          <ClinicalSuggestionsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
