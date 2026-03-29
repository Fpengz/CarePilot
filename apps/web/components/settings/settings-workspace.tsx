"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { LogOut, User, Heart, Bell, Users, Lightbulb, Shield } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { useSession } from "@/components/app/session-provider";
import { updateAuthProfile, logout } from "@/lib/api/auth-client";
import {
  getMobilityReminderSettings,
  listMessageEndpoints,
  listMessagePreferences,
  updateMobilityReminderSettings,
  updateMessageEndpoints,
  updateMessagePreferences,
} from "@/lib/api/reminder-client";
import {
  completeHealthProfileOnboarding,
  getHealthProfileOnboarding,
  updateHealthProfile,
  updateHealthProfileOnboarding,
} from "@/lib/api/profile-client";
import type {
  HealthProfile,
  MobilityReminderSettings,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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
  return value.split(",").map((item) => item.trim()).filter(Boolean);
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
      const [start_time, end_time] = (range || "00:00-00:00").split("-").map((p) => p.trim());
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
  return GUIDED_STEP_ORDER.indexOf(stepId as any) ?? 0;
}

export function SettingsWorkspace() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { status, user, refreshSession } = useSession();
  const [activeTab, setActiveTab] = useState<SettingsTab>("account");
  const [healthViewMode, setHealthViewMode] = useState<HealthViewMode>("guided");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Form states
  const [displayNameInput, setDisplayNameInput] = useState(user?.display_name ?? "");
  const [profileModeInput, setProfileModeInput] = useState<"self" | "caregiver">(user?.profile_mode ?? "self");
  const [draft, setDraft] = useState<HealthProfileDraft | null>(null);
  const [mobilityDraft, setMobilityDraft] = useState<MobilityReminderSettings | null>(null);

  const [deliverySettings, setDeliverySettings] = useState({
    inAppEnabled: true, inAppOffset: 0,
    emailEnabled: false, emailOffset: 0, emailDestination: "",
    smsEnabled: false, smsOffset: 0, smsDestination: "",
    telegramEnabled: false, telegramOffset: 0, telegramDestination: "",
  });

  // Queries
  const { data: onboarding, isLoading: onboardingLoading } = useQuery({
    queryKey: ["health-onboarding"],
    queryFn: getHealthProfileOnboarding,
    enabled: status === "authenticated",
  });

  const { data: mobility, isLoading: mobilityLoading } = useQuery({
    queryKey: ["mobility-settings"],
    queryFn: getMobilityReminderSettings,
    enabled: status === "authenticated",
  });

  const { data: prefs, isLoading: prefsLoading } = useQuery({
    queryKey: ["notification-prefs"],
    queryFn: listMessagePreferences,
    enabled: status === "authenticated",
  });

  const { data: endpoints, isLoading: endpointsLoading } = useQuery({
    queryKey: ["notification-endpoints"],
    queryFn: listMessageEndpoints,
    enabled: status === "authenticated",
  });

  // Sync drafts when data loads
  useEffect(() => {
    if (onboarding && !draft) {
      setDraft(buildDraft(onboarding.profile));
    }
    if (mobility && !mobilityDraft) {
      setMobilityDraft(mobility.settings || {});
    }
    if (prefs && endpoints) {
      const inApp = prefs.preferences.find(p => p.channel === "in_app");
      const email = prefs.preferences.find(p => p.channel === "email");
      const sms = prefs.preferences.find(p => p.channel === "sms");
      const telegram = prefs.preferences.find(p => p.channel === "telegram");
      
      const emailEnd = endpoints.endpoints.find(e => e.channel === "email");
      const smsEnd = endpoints.endpoints.find(e => e.channel === "sms");
      const telegramEnd = endpoints.endpoints.find(e => e.channel === "telegram");

      setDeliverySettings({
        inAppEnabled: inApp?.enabled ?? true, inAppOffset: inApp?.offset_minutes ?? 0,
        emailEnabled: email?.enabled ?? false, emailOffset: email?.offset_minutes ?? 0, emailDestination: emailEnd?.destination ?? "",
        smsEnabled: sms?.enabled ?? false, smsOffset: sms?.offset_minutes ?? 0, smsDestination: smsEnd?.destination ?? "",
        telegramEnabled: telegram?.enabled ?? false, telegramOffset: telegram?.offset_minutes ?? 0, telegramDestination: telegramEnd?.destination ?? "",
      });
    }
  }, [onboarding, mobility, prefs, endpoints, draft, mobilityDraft]);

  // Mutations
  const accountMutation = useMutation({
    mutationFn: updateAuthProfile,
    onSuccess: async () => {
      await refreshSession();
      setNotice("Account settings updated.");
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const logoutMutation = useMutation({
    mutationFn: logout,
    onSuccess: () => router.replace("/login"),
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const profileMutation = useMutation({
    mutationFn: (p: any) => updateHealthProfile(p),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["health-onboarding"] });
      setNotice("Health profile saved.");
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const guidedMutation = useMutation({
    mutationFn: (step: { id: string; profile: any }) => 
      step.id === "review" ? completeHealthProfileOnboarding() : updateHealthProfileOnboarding({ step_id: step.id, profile: step.profile }),
    onSuccess: (res) => {
      queryClient.setQueryData(["health-onboarding"], res);
      setNotice(activeGuidedStepId === "review" ? "Guided setup completed." : "Step saved.");
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const mobilityMutation = useMutation({
    mutationFn: updateMobilityReminderSettings,
    onSuccess: (res) => {
      setMobilityDraft(res.settings);
      setNotice("Mobility settings saved.");
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const deliveryMutation = useMutation({
    mutationFn: async (payload: any) => {
      await Promise.all([
        updateMessagePreferences({ rules: payload.rules }),
        updateMessageEndpoints({ endpoints: payload.endpoints }),
      ]);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-prefs"] });
      queryClient.invalidateQueries({ queryKey: ["notification-endpoints"] });
      setNotice("Delivery preferences saved.");
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const activeGuidedStepId = onboarding?.onboarding.current_step ?? "basic_identity";
  const activeGuidedStep = onboarding?.steps.find(s => s.id === activeGuidedStepId);
  const activeStepIndex = stepIndex(activeGuidedStepId);

  const handleDeliverySave = () => {
    deliveryMutation.mutate({
      rules: [
        { channel: "in_app", enabled: deliverySettings.inAppEnabled, offset_minutes: deliverySettings.inAppOffset },
        { channel: "email", enabled: deliverySettings.emailEnabled, offset_minutes: deliverySettings.emailOffset },
        { channel: "sms", enabled: deliverySettings.smsEnabled, offset_minutes: deliverySettings.smsOffset },
        { channel: "telegram", enabled: deliverySettings.telegramEnabled, offset_minutes: deliverySettings.telegramOffset },
      ],
      endpoints: [
        ...(deliverySettings.emailDestination ? [{ channel: "email", destination: deliverySettings.emailDestination, verified: true }] : []),
        ...(deliverySettings.smsDestination ? [{ channel: "sms", destination: deliverySettings.smsDestination, verified: false }] : []),
        ...(deliverySettings.telegramDestination ? [{ channel: "telegram", destination: deliverySettings.telegramDestination, verified: true }] : []),
      ]
    });
  };

  if (!draft || !mobilityDraft) return <div className="p-12 text-center text-sm opacity-60">Loading configuration…</div>;

  return (
    <div className="section-stack">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight" role="heading">Configuration</h1>
        <p className="text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl text-sm">
          Fine-tune your health profile, manage care circle members, and configure reminder delivery channels.
        </p>
      </div>

      {error && <ErrorCard message={error} />}
      {notice && <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</div>}

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="w-full space-y-8">
        <TabsList className="bg-transparent h-auto p-0 gap-8 border-b border-[color:var(--border-soft)] w-full justify-start">
          <TabsTrigger value="account" className="settings-tab-trigger">Identity</TabsTrigger>
          <TabsTrigger value="health" className="settings-tab-trigger">Health Profile</TabsTrigger>
          <TabsTrigger value="reminders" className="settings-tab-trigger">Delivery</TabsTrigger>
          <TabsTrigger value="household" className="settings-tab-trigger">Household</TabsTrigger>
          <TabsTrigger value="clinical_suggestions" className="settings-tab-trigger">Suggestions</TabsTrigger>
        </TabsList>

        <TabsContent value="account" className="space-y-8 mt-0">
          <Card className="glass-card">
            <CardHeader><CardTitle>Account Context</CardTitle></CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label>Display Name</Label>
                <Input value={displayNameInput} onChange={e => setDisplayNameInput(e.target.value)} className="rounded-xl" />
              </div>
              <div className="space-y-2">
                <Label>Clinical Role</Label>
                <Select value={profileModeInput} onChange={e => setProfileModeInput(e.target.value as any)}>
                  <option value="self">Managing for myself</option>
                  <option value="caregiver">Caregiver role</option>
                </Select>
              </div>
              <div className="pt-4 flex gap-3">
                <Button onClick={() => accountMutation.mutate({ display_name: displayNameInput, profile_mode: profileModeInput })} disabled={accountMutation.isPending}>
                  <AsyncLabel active={accountMutation.isPending} idle="Update Account" loading="Saving" />
                </Button>
                <Button variant="ghost" className="text-rose-600" onClick={() => logoutMutation.mutate()} disabled={logoutMutation.isPending}>
                  <AsyncLabel active={logoutMutation.isPending} idle="Sign Out" loading="Signing out" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="health" className="space-y-8 mt-0">
          <div className="flex gap-2">
            <Button variant={healthViewMode === "guided" ? "default" : "secondary"} onClick={() => setHealthViewMode("guided")}>Guided</Button>
            <Button variant={healthViewMode === "advanced" ? "default" : "secondary"} onClick={() => setHealthViewMode("advanced")}>Advanced</Button>
          </div>

          {healthViewMode === "guided" ? (
            <Card className="glass-card">
              <CardHeader><CardTitle>{activeGuidedStep?.title ?? "Guided Setup"}</CardTitle></CardHeader>
              <CardContent className="space-y-6">
                {activeGuidedStepId === "basic_identity" && (
                  <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="space-y-2"><Label>Age</Label><Input value={draft.age} onChange={e => setDraft({...draft, age: e.target.value})} /></div>
                    <div className="space-y-2"><Label>Height (cm)</Label><Input value={draft.height_cm} onChange={e => setDraft({...draft, height_cm: e.target.value})} /></div>
                    <div className="space-y-2"><Label>Weight (kg)</Label><Input value={draft.weight_kg} onChange={e => setDraft({...draft, weight_kg: e.target.value})} /></div>
                  </div>
                )}
                {/* ... other steps ... */}
                <div className="flex justify-between pt-6 border-t">
                  <Button variant="ghost" disabled={activeStepIndex === 0} onClick={() => {}}>Back</Button>
                  <Button onClick={() => guidedMutation.mutate({ id: activeGuidedStepId, profile: buildGuidedStepPayload(activeGuidedStepId, draft) })} disabled={guidedMutation.isPending}>
                    <AsyncLabel active={guidedMutation.isPending} idle={activeGuidedStepId === "review" ? "Finish" : "Continue"} loading="Saving" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="glass-card">
              <CardHeader><CardTitle>Advanced Health Profile</CardTitle></CardHeader>
              <CardContent className="space-y-6">
                <div className="grid gap-6 md:grid-cols-3">
                  <div className="space-y-2"><Label>Sodium (mg)</Label><Input value={draft.daily_sodium_limit_mg} onChange={e => setDraft({...draft, daily_sodium_limit_mg: e.target.value})} /></div>
                  <div className="space-y-2"><Label>Sugar (g)</Label><Input value={draft.daily_sugar_limit_g} onChange={e => setDraft({...draft, daily_sugar_limit_g: e.target.value})} /></div>
                </div>
                <Button onClick={() => profileMutation.mutate(buildFullProfilePayload(draft))} disabled={profileMutation.isPending}>
                  <AsyncLabel active={profileMutation.isPending} idle="Save Profile" loading="Saving" />
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="reminders" className="space-y-8 mt-0">
          <Card className="glass-card">
            <CardHeader><CardTitle>Delivery Channels</CardTitle></CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between p-4 border rounded-xl">
                <Label>In-App Notifications</Label>
                <input type="checkbox" checked={deliverySettings.inAppEnabled} onChange={e => setDeliverySettings({...deliverySettings, inAppEnabled: e.target.checked})} />
              </div>
              <div className="flex items-center justify-between p-4 border rounded-xl">
                <Label>Telegram Delivery</Label>
                <input type="checkbox" checked={deliverySettings.telegramEnabled} onChange={e => setDeliverySettings({...deliverySettings, telegramEnabled: e.target.checked})} />
              </div>
              {deliverySettings.telegramEnabled && (
                <div className="p-4 border rounded-xl space-y-2">
                  <Label>Telegram Chat ID</Label>
                  <Input value={deliverySettings.telegramDestination} onChange={e => setDeliverySettings({...deliverySettings, telegramDestination: e.target.value})} />
                </div>
              )}
              <Button onClick={handleDeliverySave} disabled={deliveryMutation.isPending} className="w-full">
                <AsyncLabel active={deliveryMutation.isPending} idle="Save Delivery Rules" loading="Saving" />
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="household" className="mt-0"><HouseholdTab /></TabsContent>
        <TabsContent value="clinical_suggestions" className="mt-0"><ClinicalSuggestionsTab /></TabsContent>
      </Tabs>
    </div>
  );
}
