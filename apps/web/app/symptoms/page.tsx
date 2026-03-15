"use client";

import { useEffect, useState } from "react";
import { Activity, AlertTriangle, RefreshCcw, Thermometer, Info, History } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { createSymptomCheckIn, getSymptomSummary, listSymptomCheckIns } from "@/lib/api/meal-client";
import type { SymptomCheckInApi, SymptomSummaryApiResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

const COMMON_SYMPTOMS = ["Headache", "Fatigue", "Nausea", "Dizziness", "Bloating", "Thirst"];

export default function SymptomsPage() {
  const [severity, setSeverity] = useState(3);
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [freeText, setFreeText] = useState("");
  const [checkIns, setCheckIns] = useState<SymptomCheckInApi[]>([]);
  const [summary, setSummary] = useState<SymptomSummaryApiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function refreshData() {
    try {
      const [checkinResponse, summaryResponse] = await Promise.all([
        listSymptomCheckIns({ limit: 20 }),
        getSymptomSummary(),
      ]);
      setCheckIns(checkinResponse.items);
      setSummary(summaryResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    void refreshData();
  }, []);

  const handleSubmit = async () => {
    setError(null);
    setLoading(true);
    try {
      await createSymptomCheckIn({
        severity,
        symptom_codes: selectedSymptoms.map(s => s.toLowerCase()),
        free_text: freeText.trim() || undefined,
        context: {},
      });
      setFreeText("");
      setSelectedSymptoms([]);
      setSeverity(3);
      await refreshData();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const toggleSymptom = (symptom: string) => {
    setSelectedSymptoms(prev => 
      prev.includes(symptom) ? prev.filter(s => s !== symptom) : [...prev, symptom]
    );
  };

  return (
    <div className="section-stack">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Symptom Monitoring</h1>
          <p className="text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl text-sm">
            Log physical signals to help your AI companion detect patterns and provide safer clinical guidance.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={refreshData} className="gap-2">
          <RefreshCcw className="h-3.5 w-3.5" /> Sync Data
        </Button>
      </div>

      {error && <ErrorCard message={error} />}

      <div className="page-grid items-start">
        <div className="space-y-8">
          <div className="clinical-card space-y-8">
            <div className="space-y-1">
              <h3 className="clinical-subtitle">Active Check-In</h3>
              <p className="clinical-body">How are you feeling right now?</p>
            </div>

            <div className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-[10px] font-bold uppercase tracking-widest opacity-70">Intensity</Label>
                  <span className={cn(
                    "text-xs font-bold px-2 py-0.5 rounded-full",
                    severity >= 4 ? "bg-rose-500/10 text-rose-600" : "bg-[color:var(--accent)]/10 text-[color:var(--accent)]"
                  )}>Level {severity}</span>
                </div>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((val) => (
                    <button
                      key={val}
                      onClick={() => setSeverity(val)}
                      className={cn(
                        "flex-1 h-12 rounded-xl border-2 transition-all font-bold",
                        severity === val 
                          ? "border-[color:var(--accent)] bg-[color:var(--accent)] text-white shadow-sm" 
                          : "border-[color:var(--border-soft)] bg-[color:var(--surface)] text-[color:var(--muted-foreground)] hover:border-[color:var(--border)]"
                      )}
                    >
                      {val}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <Label className="text-[10px] font-bold uppercase tracking-widest opacity-70">Symptoms</Label>
                <div className="flex flex-wrap gap-2">
                  {COMMON_SYMPTOMS.map((s) => (
                    <button
                      key={s}
                      onClick={() => toggleSymptom(s)}
                      className={cn(
                        "clinical-chip transition-all",
                        selectedSymptoms.includes(s) 
                          ? "bg-[color:var(--accent)] text-white border-[color:var(--accent)]" 
                          : "hover:bg-[color:var(--muted)]"
                      )}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <Label className="text-[10px] font-bold uppercase tracking-widest opacity-70">Clinical Notes</Label>
                <Textarea
                  placeholder="Describe timing, duration, or triggers..."
                  value={freeText}
                  onChange={(e) => setFreeText(e.target.value)}
                  className="rounded-xl min-h-[100px]"
                />
              </div>

              <Button 
                className="w-full h-12 rounded-xl font-bold shadow-sm" 
                onClick={handleSubmit}
                disabled={loading}
              >
                <AsyncLabel active={loading} loading="Recording" idle="Log Symptom Check-In" />
              </Button>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-[color:var(--muted-foreground)]" />
              <h4 className="text-xs font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Recent Records</h4>
            </div>
            <div className="grid gap-3">
              {checkIns.slice(0, 5).map((item) => (
                <div key={item.id} className="data-list-row group">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-lg border",
                        item.severity >= 4 ? "bg-rose-500/10 text-rose-600 border-rose-200" : "bg-emerald-500/10 text-emerald-600 border-emerald-200"
                      )}>
                        <Thermometer className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="text-sm font-bold tracking-tight">Severity {item.severity}</div>
                        <div className="text-[10px] text-[color:var(--muted-foreground)] opacity-60">
                          {new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.recorded_at))}
                        </div>
                      </div>
                    </div>
                    <Badge 
                      variant="outline" 
                      className={cn(
                        "text-[10px] uppercase tracking-tighter",
                        item.safety.decision === "escalate" ? "bg-rose-50 text-rose-600 border-rose-200" : ""
                      )}
                    >
                      {item.safety.decision}
                    </Badge>
                  </div>
                  {item.free_text && (
                    <p className="mt-2 text-xs text-[color:var(--muted-foreground)] line-clamp-2 italic">&quot;{item.free_text}&quot;</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-8 lg:sticky lg:top-28">
          <div className="clinical-card bg-[color:var(--accent)]/5 border-[color:var(--accent)]/10">
            <div className="flex items-center gap-2 text-[color:var(--accent)] mb-4">
              <Info className="h-4 w-4" />
              <span className="text-[10px] font-bold uppercase tracking-widest">Aggregate Insights</span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <div className="text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-70">Total Logs</div>
                <div className="text-xl font-bold">{summary?.total_count ?? 0}</div>
              </div>
              <div className="space-y-1">
                <div className="text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-70">Avg Intensity</div>
                <div className="text-xl font-bold">{(summary?.average_severity ?? 0).toFixed(1)}</div>
              </div>
            </div>
            {summary?.red_flag_count ? (
              <div className="mt-6 rounded-lg bg-rose-50 p-3 border border-rose-100 flex items-center gap-3">
                <AlertTriangle className="h-4 w-4 text-rose-600" />
                <span className="text-xs font-bold text-rose-700">{summary.red_flag_count} Critical Red Flags Detected</span>
              </div>
            ) : null}
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-[color:var(--muted-foreground)]" />
              <h4 className="text-xs font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Prevalent Signals</h4>
            </div>
            <div className="flex flex-wrap gap-2">
              {summary?.top_symptoms.map((s) => (
                <div key={s.code} className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[color:var(--border-soft)] bg-[color:var(--surface)] text-xs font-medium">
                  <span className="capitalize">{s.code}</span>
                  <span className="text-[10px] font-bold text-[color:var(--accent)] bg-[color:var(--accent)]/5 px-1.5 py-0.5 rounded-md">{s.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
