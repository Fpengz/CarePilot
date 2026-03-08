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
        tags={["summary-first", "meal tracking", "daily guidance"]}
      />

      {status === "unauthenticated" ? <ErrorCard message="Sign in to view your daily dashboard." /> : null}
      {error ? <ErrorCard message={error} /> : null}

      <div className="mb-4 flex flex-wrap gap-2">
        <Button asChild>
          <Link href="/settings">Open Settings</Link>
        </Button>
        <Button asChild variant="secondary">
          <Link href="/meals">Open Meals</Link>
        </Button>
        <Button asChild variant="secondary">
          <Link href="/reminders">Open Reminders</Link>
        </Button>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Profile Readiness</CardTitle>
            <CardDescription>Keep your structured health profile current so recommendations can stay targeted.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
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
              <div className="mt-1 text-sm font-semibold">
                {profile?.completeness.missing_fields.length
                  ? profile.completeness.missing_fields.join(", ")
                  : "Profile is ready for personalized guidance."}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Today’s Intake Snapshot</CardTitle>
            <CardDescription>Daily progress now lives on the Meals page, with this dashboard showing the headline view.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            <div className="metric-card">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Meals logged</div>
              <div className="mt-1 text-sm font-semibold">{dailySummary?.meal_count ?? 0}</div>
            </div>
            <div className="metric-card">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Remaining calories</div>
              <div className="mt-1 text-sm font-semibold">{Math.round(dailySummary?.remaining.calories ?? 0)} kcal</div>
            </div>
            <div className="metric-card">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Protein remaining</div>
              <div className="mt-1 text-sm font-semibold">{Math.round(dailySummary?.remaining.protein_g ?? 0)} g</div>
            </div>
            <div className="metric-card">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Fiber remaining</div>
              <div className="mt-1 text-sm font-semibold">{Math.round(dailySummary?.remaining.fiber_g ?? 0)} g</div>
            </div>
            <div className="metric-card sm:col-span-2">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Most recent meal log</div>
              <div className="mt-1 text-sm font-semibold">{formatWhen(dailySummary?.last_logged_at)}</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Potential Gaps and Imbalances</CardTitle>
            <CardDescription>Cautious pattern guidance based on recent logs, not diagnostic results.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {insightSummary.length > 0 ? (
              insightSummary.map((insight) => (
                <div key={insight.code} className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]">
                  <div className="text-sm font-semibold">{insight.title}</div>
                  <p className="app-muted mt-1 text-sm">{insight.summary}</p>
                </div>
              ))
            ) : (
              <p className="app-muted text-sm">Log a few more meals across several days to unlock pattern-level guidance.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Next Guidance</CardTitle>
            <CardDescription>What needs attention next across reminders and meal suggestions.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="metric-card">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Next reminder</div>
              <div className="mt-1 text-sm font-semibold">{nextReminder?.title ?? "No pending reminder"}</div>
              <div className="app-muted mt-1 text-xs">{formatWhen(nextReminder?.scheduled_at)}</div>
            </div>
            <div className="metric-card">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Suggested next meal</div>
              <div className="mt-1 text-sm font-semibold">{firstSuggestion?.title ?? "Waiting for suggestions"}</div>
              <div className="app-muted mt-1 text-xs">
                {firstSuggestion ? firstSuggestion.why_it_fits.join(" ") : "Complete your profile and meal logging for sharper guidance."}
              </div>
            </div>
          </CardContent>
        </Card>

        {showCaregiverCard ? (
          <Card>
            <CardHeader>
              <CardTitle>Caregiving View</CardTitle>
              <CardDescription>Read-only household monitoring now lives on the Household page.</CardDescription>
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
  );
}
