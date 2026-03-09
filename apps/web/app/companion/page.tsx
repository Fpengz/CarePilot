"use client";

import { useEffect, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { getCompanionToday, runCompanionInteraction } from "@/lib/api/companion-client";
import type { CompanionInteractionApiResponse, CompanionTodayApiResponse } from "@/lib/types";

const INTERACTION_PRESETS: Record<
  "chat" | "meal_review" | "check_in" | "report_follow_up" | "adherence_follow_up",
  { label: string; message: string; emotionText: string }
> = {
  chat: {
    label: "Chat",
    message: "Explain why my current pattern matters and what I should focus on first.",
    emotionText: "I want a clearer explanation without being overwhelmed.",
  },
  meal_review: {
    label: "Meal Review",
    message: "I had another oily hawker lunch. Give me one realistic food swap for the next meal.",
    emotionText: "I feel discouraged about repeating the same lunch choices.",
  },
  check_in: {
    label: "Check-In",
    message: "Help me decide on one realistic next step for today.",
    emotionText: "I feel a bit discouraged about staying consistent.",
  },
  report_follow_up: {
    label: "Report Follow-Up",
    message: "My report looks worrying. What is the main thing I should follow up on now?",
    emotionText: "I am anxious about what the latest results mean.",
  },
  adherence_follow_up: {
    label: "Adherence Follow-Up",
    message: "I missed my meds again because I was rushing. Help me protect the next dose.",
    emotionText: "I feel stressed and frustrated about missing medications.",
  },
};

type InteractionType = keyof typeof INTERACTION_PRESETS;

export default function CompanionPage() {
  const [today, setToday] = useState<CompanionTodayApiResponse | null>(null);
  const [interaction, setInteraction] = useState<CompanionInteractionApiResponse | null>(null);
  const [interactionType, setInteractionType] = useState<InteractionType>("check_in");
  const [message, setMessage] = useState(INTERACTION_PRESETS.check_in.message);
  const [emotionText, setEmotionText] = useState(INTERACTION_PRESETS.check_in.emotionText);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<"today" | "interaction" | null>(null);

  async function refreshToday() {
    const response = await getCompanionToday();
    setToday(response);
    setInteraction(null);
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading("today");
        const response = await getCompanionToday();
        if (!cancelled) {
          setToday(response);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(null);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const active = interaction ?? today;
  const citationList = active?.care_plan.citations ?? [];
  const deltaEntries = Object.entries(active?.impact.deltas ?? {});

  return (
    <div>
      <PageTitle
        eyebrow="Companion"
        title="AI Health Companion"
        description="Turn meals, reminders, symptoms, biomarkers, and patient intent into one next-best action, one clinician-ready rationale, and one impact signal to watch."
        tags={["proactive guidance", "supporting evidence", "clinician digest"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Interactive Care Session</CardTitle>
            <CardDescription>Choose the interaction type, describe the barrier or question, and let the companion tailor the next step.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Button
                disabled={loading !== null}
                onClick={async () => {
                  setError(null);
                  setLoading("today");
                  try {
                    await refreshToday();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoading(null);
                  }
                }}
              >
                <AsyncLabel active={loading === "today"} idle="Refresh Today" loading="Refreshing" />
              </Button>
              {active ? (
                <>
                  <Badge variant={active.engagement.risk_level === "high" ? "default" : "outline"}>
                    Risk: {active.engagement.risk_level}
                  </Badge>
                  <Badge variant="outline">Mode: {active.engagement.recommended_mode}</Badge>
                  <Badge variant="outline">Policy: {active.care_plan.policy_status}</Badge>
                </>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="companion-interaction-type">Interaction Type</Label>
              <Select
                id="companion-interaction-type"
                value={interactionType}
                onChange={(event) => {
                  const nextType = event.target.value as InteractionType;
                  setInteractionType(nextType);
                  setMessage(INTERACTION_PRESETS[nextType].message);
                  setEmotionText(INTERACTION_PRESETS[nextType].emotionText);
                }}
              >
                {Object.entries(INTERACTION_PRESETS).map(([value, preset]) => (
                  <option key={value} value={value}>
                    {preset.label}
                  </option>
                ))}
              </Select>
            </div>

            <div className="rounded-xl border border-[color:var(--border)] bg-white/70 p-4 dark:bg-[color:var(--panel-soft)]">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Today&apos;s Priority</div>
              <div className="mt-1 text-lg font-semibold">{active?.care_plan.headline ?? "Loading companion state…"}</div>
              <p className="app-muted mt-2 text-sm">{active?.care_plan.summary ?? "No care plan loaded yet."}</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="companion-message">Patient Message</Label>
              <Textarea
                id="companion-message"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                rows={4}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="companion-emotion">Optional Emotional Context</Label>
              <Input
                id="companion-emotion"
                value={emotionText}
                onChange={(event) => setEmotionText(event.target.value)}
              />
            </div>
            <Button
              disabled={loading !== null || !message.trim()}
              onClick={async () => {
                setError(null);
                setLoading("interaction");
                try {
                  const response = await runCompanionInteraction({
                    interaction_type: interactionType,
                    message,
                    emotion_text: emotionText.trim() || undefined,
                  });
                  setInteraction(response);
                } catch (e) {
                  setError(e instanceof Error ? e.message : String(e));
                } finally {
                  setLoading(null);
                }
              }}
            >
              <AsyncLabel active={loading === "interaction"} idle="Generate Next Step" loading="Thinking" />
            </Button>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}
          <Card>
            <CardHeader>
              <CardTitle>Recommended Next Step</CardTitle>
              <CardDescription>The companion turns the current state and message intent into a bounded plan.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {active?.care_plan.recommended_actions?.length ? (
                active.care_plan.recommended_actions.map((item) => (
                  <div key={item} className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 text-sm dark:bg-[color:var(--panel-soft)]">
                    {item}
                  </div>
                ))
              ) : (
                <p className="app-muted text-sm">No companion actions yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Why This Matters</CardTitle>
              <CardDescription>Reasoning and timing signals explain why the companion chose this intervention now.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]">
                {active?.care_plan.why_now ?? "No why-now rationale yet."}
              </div>
              <div className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]">
                {active?.care_plan.reasoning_summary ?? "No reasoning summary yet."}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Supporting Evidence</CardTitle>
              <CardDescription>These evidence notes support the current recommendation and clinician-facing summary.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {citationList.length ? (
                citationList.map((item) => (
                  <div key={`${item.title}-${item.relevance}`} className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-medium">{item.title}</div>
                      <Badge variant="outline">{Math.round(item.confidence * 100)}%</Badge>
                    </div>
                    <p className="app-muted mt-2 text-sm">{item.summary}</p>
                    <p className="mt-2 text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">{item.relevance}</p>
                  </div>
                ))
              ) : (
                <p className="app-muted text-sm">No supporting evidence yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Clinician Digest Preview</CardTitle>
              <CardDescription>Preview the low-burden summary a clinician would see if this needs follow-up.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]">
                <div className="font-medium">{interaction?.clinician_digest_preview.summary ?? "Run an interaction to preview the digest."}</div>
                <p className="app-muted mt-2">{interaction?.clinician_digest_preview.why_now ?? "No clinician rationale yet."}</p>
              </div>
              {interaction?.clinician_digest_preview.what_changed?.slice(0, 3).map((item) => (
                <div key={item} className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]">
                  {item}
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Impact to Watch</CardTitle>
              <CardDescription>Track which metric gaps should improve if the patient follows through on this plan.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]">
                <div className="font-medium">
                  {`${active?.impact.baseline_window ?? "No baseline window yet"} -> ${active?.impact.comparison_window ?? "No follow-up window yet"}`}
                </div>
                <p className="app-muted mt-2">
                  {active?.impact.interventions_measured?.join(", ") ?? "No measured interventions yet."}
                </p>
              </div>
              {deltaEntries.length ? (
                <div className="grid gap-3 md:grid-cols-2">
                  {deltaEntries.map(([key, value]) => (
                    <div key={key} className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">{key}</div>
                      <div className="mt-2 text-xl font-semibold">{value.toFixed(2)}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">No impact deltas yet.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
