"use client";

import { useEffect, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { createSymptomCheckIn, getSymptomSummary, listSymptomCheckIns } from "@/lib/api";
import type { SymptomCheckInApi, SymptomSummaryApiResponse } from "@/lib/types";

type LoadingAction = "submit" | "refresh" | null;

function parseSymptomCodes(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function SymptomsPage() {
  const [severity, setSeverity] = useState("3");
  const [codesInput, setCodesInput] = useState("headache,fatigue");
  const [freeText, setFreeText] = useState("Mild headache after lunch");
  const [checkIns, setCheckIns] = useState<SymptomCheckInApi[]>([]);
  const [summary, setSummary] = useState<SymptomSummaryApiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<LoadingAction>(null);

  async function refreshData() {
    const [checkinResponse, summaryResponse] = await Promise.all([
      listSymptomCheckIns({ limit: 20 }),
      getSymptomSummary(),
    ]);
    setCheckIns(checkinResponse.items);
    setSummary(summaryResponse);
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoadingAction("refresh");
        const [checkinResponse, summaryResponse] = await Promise.all([
          listSymptomCheckIns({ limit: 20 }),
          getSymptomSummary(),
        ]);
        if (cancelled) return;
        setCheckIns(checkinResponse.items);
        setSummary(summaryResponse);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoadingAction(null);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <PageTitle
        eyebrow="Symptoms"
        title="Symptom Check-Ins and Safety Triage"
        description="Log symptom severity and notes, then review safety decisions and symptom trends."
        tags={["check-ins", "safety gate", "summary metrics"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Symptom Check-In</CardTitle>
            <CardDescription>Creates `POST /api/v1/symptoms/check-ins` entries with automated safety triage.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="symptom-severity">Severity (1-5)</Label>
                <Select id="symptom-severity" value={severity} onChange={(event) => setSeverity(event.target.value)}>
                  <option value="1">1 - Very mild</option>
                  <option value="2">2 - Mild</option>
                  <option value="3">3 - Moderate</option>
                  <option value="4">4 - Strong</option>
                  <option value="5">5 - Severe</option>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="symptom-codes">Symptom codes (CSV)</Label>
                <Textarea
                  id="symptom-codes"
                  rows={2}
                  value={codesInput}
                  onChange={(event) => setCodesInput(event.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="symptom-notes">Notes</Label>
              <Textarea
                id="symptom-notes"
                rows={4}
                value={freeText}
                onChange={(event) => setFreeText(event.target.value)}
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                disabled={loadingAction !== null}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("submit");
                  try {
                    await createSymptomCheckIn({
                      severity: Math.max(1, Math.min(5, Number(severity) || 3)),
                      symptom_codes: parseSymptomCodes(codesInput),
                      free_text: freeText.trim() || undefined,
                      context: {},
                    });
                    await refreshData();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "submit"} loading="Submitting" idle="Submit Check-In" />
              </Button>
              <Button
                variant="secondary"
                disabled={loadingAction !== null}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("refresh");
                  try {
                    await refreshData();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "refresh"} loading="Refreshing" idle="Refresh Summary" />
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Symptom Summary</CardTitle>
              <CardDescription>Aggregated counts and severity from persisted check-ins.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Total check-ins</div>
                  <div className="mt-1 text-xl font-semibold">{summary?.total_count ?? 0}</div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Average severity</div>
                  <div className="mt-1 text-xl font-semibold">{(summary?.average_severity ?? 0).toFixed(2)}</div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Red-flag count</div>
                  <div className="mt-1 text-xl font-semibold">{summary?.red_flag_count ?? 0}</div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Latest record</div>
                  <div className="mt-1 text-sm font-semibold">
                    {summary?.latest_recorded_at ? new Date(summary.latest_recorded_at).toLocaleString() : "None"}
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                <div className="text-sm font-semibold">Top symptoms</div>
                {summary?.top_symptoms.length ? (
                  <div className="flex flex-wrap gap-2">
                    {summary.top_symptoms.map((item) => (
                      <Badge key={item.code} variant="outline">
                        {item.code} ({item.count})
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="app-muted text-sm">No symptom trends available yet.</p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Recent Check-Ins</CardTitle>
              <CardDescription>Latest records with safety decisions.</CardDescription>
            </CardHeader>
            <CardContent>
              {checkIns.length > 0 ? (
                <div className="data-list">
                  {checkIns.slice(0, 10).map((item) => (
                    <div key={item.id} className="data-list-row gap-2">
                      <div className="flex items-center gap-2">
                        <div className="text-sm font-medium">Severity {item.severity}</div>
                        <Badge variant={item.safety.decision === "escalate" ? "default" : "outline"}>
                          {item.safety.decision}
                        </Badge>
                      </div>
                      <div className="app-muted text-xs">{new Date(item.recorded_at).toLocaleString()}</div>
                      <div className="app-muted text-xs">
                        {item.symptom_codes.length ? item.symptom_codes.join(", ") : "No codes"}
                      </div>
                      {item.free_text ? <div className="text-sm">{item.free_text}</div> : null}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">No symptom check-ins yet.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
