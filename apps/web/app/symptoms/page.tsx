"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Activity, AlertTriangle, RefreshCcw, Thermometer, Info, History } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { createSymptomCheckIn, getSymptomSummary, listSymptomCheckIns } from "@/lib/api/meal-client";
import { cn } from "@/lib/utils";

const COMMON_SYMPTOMS = ["Headache", "Fatigue", "Nausea", "Dizziness", "Bloating", "Thirst"];

export default function SymptomsPage() {
  const queryClient = useQueryClient();
  const [severity, setSeverity] = useState(3);
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [freeText, setFreeText] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Queries
  const { data: checkinsData, isLoading: checkinsLoading } = useQuery({
    queryKey: ["symptom-checkins"],
    queryFn: () => listSymptomCheckIns({ limit: 20 }),
  });

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["symptom-summary"],
    queryFn: () => getSymptomSummary(),
  });

  const checkIns = checkinsData?.items ?? [];

  // Mutations
  const submitMutation = useMutation({
    mutationFn: createSymptomCheckIn,
    onSuccess: () => {
      setFreeText("");
      setSelectedSymptoms([]);
      setSeverity(3);
      queryClient.invalidateQueries({ queryKey: ["symptom-checkins"] });
      queryClient.invalidateQueries({ queryKey: ["symptom-summary"] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const toggleSymptom = (symptom: string) => {
    setSelectedSymptoms(prev => 
      prev.includes(symptom) ? prev.filter(s => s !== symptom) : [...prev, symptom]
    );
  };

  const loading = checkinsLoading || summaryLoading || submitMutation.isPending;

  return (
    <div className="section-stack relative isolate">
      <div className="dashboard-grounding" />
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Symptom Monitoring</h1>
          <p className="text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl text-sm">
            Log physical signals to help your AI companion detect patterns and provide safer clinical guidance.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => queryClient.invalidateQueries()} className="gap-2 rounded-xl h-10 px-4">
          <RefreshCcw className="h-3.5 w-3.5" /> Sync Data
        </Button>
      </div>

      {error && <ErrorCard message={error} />}

      <div className="grid grid-cols-12 gap-6 items-start">
        <div className="col-span-12 lg:col-span-8 space-y-8">
          <div className="glass-card space-y-8">
            <div className="space-y-1">
              <h3 className="text-base font-bold">Active Check-In</h3>
              <p className="text-xs text-[color:var(--muted-foreground)]">How are you feeling right now?</p>
            </div>

            <div className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-[10px] font-bold uppercase tracking-widest opacity-70">Intensity</Label>
                  <span className={cn(
                    "status-chip",
                    severity >= 4 ? "status-chip-rose" : "status-chip-teal"
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
                          ? "border-health-teal bg-health-teal text-white shadow-sm" 
                          : "border-white/10 bg-white/5 text-[color:var(--muted-foreground)] hover:border-white/20"
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
                        "status-chip border-2 transition-all",
                        selectedSymptoms.includes(s) 
                          ? "status-chip-teal border-health-teal bg-health-teal text-white" 
                          : "status-chip-slate border-white/10 hover:border-white/20"
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
                  className="rounded-xl min-h-[100px] bg-white/5 border-white/10"
                />
              </div>

              <Button 
                className="w-full h-12 rounded-xl font-bold shadow-md bg-health-teal hover:bg-health-teal/90" 
                onClick={() => submitMutation.mutate({ severity, symptom_codes: selectedSymptoms.map(s => s.toLowerCase()), free_text: freeText.trim() || undefined, context: {} })}
                disabled={submitMutation.isPending}
              >
                <AsyncLabel active={submitMutation.isPending} loading="Recording" idle="Log Symptom Check-In" />
              </Button>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-[color:var(--muted-foreground)]" />
              <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)]">Recent Records</h4>
            </div>
            <div className="grid gap-3">
              {checkIns.slice(0, 5).map((item) => (
                <div key={item.id} className="glass-card !p-4 group">
                  <div className="flex items-center justify-between text-left">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-lg border border-white/10",
                        item.severity >= 4 ? "bg-health-rose-soft text-health-rose" : "bg-health-teal-soft text-health-teal"
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
                    <span 
                      className={cn(
                        "status-chip",
                        item.safety.decision === "escalate" ? "status-chip-rose" : "status-chip-slate"
                      )}
                    >
                      {item.safety.decision}
                    </span>
                  </div>
                  {item.free_text && (
                    <p className="mt-3 text-xs text-[color:var(--muted-foreground)] leading-relaxed italic border-l-2 border-white/10 pl-3">&quot;{item.free_text}&quot;</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-4 space-y-8 lg:sticky lg:top-28">
          <div className="glass-card bg-health-amber-soft border-health-amber/20 shadow-[0_8px_32px_rgba(245,158,11,0.1)]">
            <div className="flex items-center gap-2 text-health-amber mb-4">
              <Info className="h-4 w-4" />
              <span className="text-[10px] font-bold uppercase tracking-[0.2em]">Aggregate Insights</span>
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
              <div className="mt-6 rounded-lg bg-health-rose-soft p-3 border border-health-rose/20 flex items-center gap-3 animate-pulse">
                <AlertTriangle className="h-4 w-4 text-health-rose" />
                <span className="text-xs font-bold text-health-rose">{summary.red_flag_count} Critical Red Flags Detected</span>
              </div>
            ) : null}
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-[color:var(--muted-foreground)]" />
              <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)]">Prevalent Signals</h4>
            </div>
            <div className="flex flex-wrap gap-2">
              {summary?.top_symptoms.map((s) => (
                <div key={s.code} className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 text-xs font-bold shadow-sm">
                  <span className="capitalize">{s.code}</span>
                  <span className="text-[10px] font-bold text-health-teal bg-health-teal-soft px-1.5 py-0.5 rounded-md">{s.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
