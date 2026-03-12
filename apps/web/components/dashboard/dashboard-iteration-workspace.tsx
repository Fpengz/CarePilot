"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { useSession } from "@/components/app/session-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getCurrentHousehold } from "@/lib/api/household-client";
import { getMealDailySummary } from "@/lib/api/meal-client";
import { getDailySuggestions } from "@/lib/api/recommendation-client";
import { listReminders } from "@/lib/api/reminder-client";
import { getHealthProfile } from "@/lib/api/profile-client";
import type {
  DailySuggestionCard,
  DailySuggestionsResponse,
  HealthProfile,
  HouseholdBundleApiResponse,
  MealDailySummaryApiResponse,
  ReminderEventView,
} from "@/lib/types";

function formatWhen(value: string | null | undefined): string {
  if (!value) return "Not scheduled";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(parsed);
}

export function DashboardIterationWorkspace() {
  const { status, user } = useSession();
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<HealthProfile | null>(null);
  const [dailySummary, setDailySummary] = useState<MealDailySummaryApiResponse | null>(null);
  const [dailySuggestions, setDailySuggestions] = useState<DailySuggestionsResponse | null>(null);
  const [reminders, setReminders] = useState<ReminderEventView[]>([]);
  const [household, setHousehold] = useState<HouseholdBundleApiResponse | null>(null);

  useEffect(() => {
    if (status !== "authenticated") return;
    let cancelled = false;
    async function load() {
      setError(null);
      try {
        const [profileResponse, summaryResponse, suggestionResponse, reminderResponse, householdResponse] =
          await Promise.all([
          getHealthProfile(),
          getMealDailySummary(new Date().toISOString().slice(0, 10)),
          getDailySuggestions(),
          listReminders(),
          getCurrentHousehold(),
          ]);
        if (cancelled) return;
        setProfile(profileResponse.profile);
        setDailySummary(summaryResponse);
        setDailySuggestions(suggestionResponse);
        setReminders(reminderResponse.reminders);
        setHousehold(householdResponse);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [status]);

  const nextReminder = useMemo(
    () =>
      reminders
        .filter((item) => item.status === "sent")
        .sort((left, right) => left.scheduled_at.localeCompare(right.scheduled_at))[0] ?? null,
    [reminders],
  );

  const firstSuggestion = useMemo<DailySuggestionCard | null>(() => {
    if (!dailySuggestions) return null;
    for (const slot of ["breakfast", "lunch", "dinner", "snack"] as const) {
      const item = dailySuggestions.bundle.suggestions[slot];
      if (item) return item;
    }
    return null;
  }, [dailySuggestions]);

  const insightSummary = dailySummary?.insights.slice(0, 2) ?? [];
  const showCaregiverCard = user?.profile_mode === "caregiver" && Boolean(household?.household);

  return (
    <div>
      <PageTitle
        eyebrow="Overview"
        title="Today at a Glance"
        description="A cleaner dashboard for quick status checks. Use Settings, Meals, and Reminders for the detailed workflows."
      />

      {status === "unauthenticated" ? <ErrorCard message="Sign in to view your daily dashboard." /> : null}
      {error ? <ErrorCard message={error} /> : null}

      <div className="clinical-panel">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="clinical-kicker">Daily summary</div>
            <h3 className="mt-2 text-xl font-semibold leading-tight">Patient status at a glance</h3>
            <p className="clinical-body mt-2 max-w-[64ch]">
              Review today&apos;s nutrition progress, emerging risks, and the next actions for care continuity.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button asChild>
              <Link href="/meals">Log Meal</Link>
            </Button>
            <Button asChild variant="secondary">
              <Link href="/reminders">Review Reminders</Link>
            </Button>
            <Button asChild variant="secondary">
              <Link href="/settings">Update Profile</Link>
            </Button>
          </div>
        </div>
        <div className="clinical-divider my-6" />
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="metric-card">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Meals logged</div>
              <div className="mt-1 text-2xl font-semibold">{dailySummary?.meal_count ?? 0}</div>
              <p className="app-muted mt-1 text-xs">Last entry {formatWhen(dailySummary?.last_logged_at)}</p>
            </div>
            <div className="metric-card">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Remaining calories</div>
              <div className="mt-1 text-2xl font-semibold">{Math.round(dailySummary?.remaining.calories ?? 0)} kcal</div>
              <p className="app-muted mt-1 text-xs">Keep pace with your daily budget.</p>
            </div>
            <div className="metric-card">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Protein remaining</div>
              <div className="mt-1 text-2xl font-semibold">{Math.round(dailySummary?.remaining.protein_g ?? 0)} g</div>
              <p className="app-muted mt-1 text-xs">Targeted toward muscle preservation.</p>
            </div>
            <div className="metric-card">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Fiber remaining</div>
              <div className="mt-1 text-2xl font-semibold">{Math.round(dailySummary?.remaining.fiber_g ?? 0)} g</div>
              <p className="app-muted mt-1 text-xs">Supports glycemic stability.</p>
            </div>
          </div>
          <div className="clinical-card">
            <div className="clinical-kicker">Next guidance</div>
            <h4 className="mt-2 text-lg font-semibold">Immediate priorities</h4>
            <div className="mt-4 space-y-4">
              <div className="soft-block">
                <div className="text-sm font-semibold">Next reminder</div>
                <div className="app-muted mt-1 text-xs">{nextReminder?.title ?? "No pending reminder"}</div>
                <div className="app-muted mt-2 text-xs">{formatWhen(nextReminder?.scheduled_at)}</div>
              </div>
              <div className="soft-block">
                <div className="text-sm font-semibold">Suggested next meal</div>
                <div className="app-muted mt-1 text-xs">{firstSuggestion?.title ?? "Waiting for suggestions"}</div>
                <div className="app-muted mt-2 text-xs">
                  {firstSuggestion ? firstSuggestion.why_it_fits.join(" ") : "Complete your profile for sharper guidance."}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-7 grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>AI Health Alerts</CardTitle>
            <CardDescription>Pattern-based cues to review with clinical judgement.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {insightSummary.length > 0 ? (
              insightSummary.map((insight) => (
                <div key={insight.code} className="clinical-alert">
                  <div className="clinical-subtitle">{insight.title}</div>
                  <p className="app-muted mt-1 text-sm">{insight.summary}</p>
                </div>
              ))
            ) : (
              <p className="app-muted text-sm">Log more meals across several days to unlock pattern-level guidance.</p>
            )}
          </CardContent>
        </Card>

        <div className="section-stack">
          <div className="clinical-card">
            <div className="clinical-kicker">Profile signals</div>
            <h4 className="mt-2 text-lg font-semibold">Clinical context readiness</h4>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="metric-card">
                <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Profile state</div>
                <div className="mt-1 text-sm font-semibold">{profile?.completeness.state ?? "loading"}</div>
              </div>
              <div className="metric-card">
                <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">BMI</div>
                <div className="mt-1 text-sm font-semibold">
                  {profile?.bmi == null ? "Add height and weight in Settings" : profile.bmi.toFixed(1)}
                </div>
              </div>
              <div className="metric-card sm:col-span-2">
                <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Missing context</div>
                <div className="mt-1 line-clamp-2 text-sm font-semibold">
                  {profile?.completeness.missing_fields.length
                    ? profile.completeness.missing_fields.join(", ")
                    : "Profile is ready for personalized guidance."}
                </div>
              </div>
            </div>
          </div>

          {showCaregiverCard ? (
            <Card>
              <CardHeader>
                <CardTitle>Caregiving View</CardTitle>
                <CardDescription>Quick view of your active household member&apos;s status.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Household</div>
                  <div className="mt-1 text-sm font-semibold">{household?.household?.name ?? "No active household"}</div>
                  <div className="app-muted mt-1 text-xs">
                    {household?.active_household_id ? "Session household selected for caregiving." : "Set an active household in Household to narrow the view."}
                  </div>
                </div>
                <Button asChild>
                  <Link href="/household">Open Household Monitoring</Link>
                </Button>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
