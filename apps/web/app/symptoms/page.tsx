"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Activity, AlertTriangle, RefreshCcw, Thermometer, Info, History } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
    <div className="section-stack max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pb-12 bg-background min-h-screen relative isolate">
      <div className="dashboard-grounding" />
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between py-10">
        <div className="space-y-2">
          <h1 className="text-h1 font-display tracking-tight text-foreground">Symptom Monitoring</h1>
          <p className="text-muted-foreground leading-relaxed max-w-2xl text-sm font-medium">
            Log physical signals to help your AI companion detect patterns and provide safer clinical guidance.
          </p>
        </div>
        <div className="pb-1">
          <Button variant="secondary" size="sm" onClick={() => queryClient.invalidateQueries()} className="gap-2 rounded-xl h-11 px-6 bg-surface shadow-sm border-border-soft hover:bg-panel transition-all">
            <RefreshCcw className="h-4 w-4 text-accent-teal" /> Sync Clinical Data
          </Button>
        </div>
      </div>

      {error && <ErrorCard message={error} />}

      <div className="grid grid-cols-12 gap-12 items-start">
        <div className="col-span-12 lg:col-span-8 space-y-12">
          <div className="bg-panel border border-border-soft rounded-3xl p-8 shadow-sm space-y-8">
            <div className="space-y-1">
              <h3 className="text-xl font-semibold tracking-tight text-foreground">Active Check-In</h3>
              <p className="text-sm text-muted-foreground font-medium">How are you feeling right now?</p>
            </div>

            <div className="space-y-8">
              <div className="space-y-4">
                <div className="flex items-center justify-between px-1">
                  <Label className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground">Intensity Level</Label>
                  <Badge variant="outline" className={cn(
                    "text-micro-label font-bold uppercase px-3 py-1",
                    severity >= 4 ? "bg-rose-50 text-rose-600 border-rose-100" : "bg-emerald-50 text-emerald-600 border-emerald-100"
                  )}>Level {severity}</Badge>
                </div>
                <div className="flex gap-3">
                  {[1, 2, 3, 4, 5].map((val) => (
                    <button
                      key={val}
                      onClick={() => setSeverity(val)}
                      className={cn(
                        "flex-1 h-12 rounded-2xl border-2 transition-all font-bold text-sm",
                        severity === val 
                          ? "border-accent-teal bg-accent-teal text-white shadow-md transform scale-[1.02]" 
                          : "border-border-soft bg-surface text-muted-foreground hover:border-accent-teal/30 shadow-sm"
                      )}
                    >
                      {val}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-4">
                <Label className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground ml-1">Observed Symptoms</Label>
                <div className="flex flex-wrap gap-2.5">
                  {COMMON_SYMPTOMS.map((s) => (
                    <button
                      key={s}
                      onClick={() => toggleSymptom(s)}
                      className={cn(
                        "rounded-xl border-2 px-4 py-2 text-xs font-bold transition-all shadow-sm",
                        selectedSymptoms.includes(s) 
                          ? "border-accent-teal bg-accent-teal text-white" 
                          : "border-border-soft bg-surface text-muted-foreground hover:border-accent-teal/30"
                      )}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-4">
                <Label className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground ml-1">Clinical Narrative</Label>
                <Textarea
                  placeholder="Describe timing, duration, or triggers..."
                  value={freeText}
                  onChange={(e) => setFreeText(e.target.value)}
                  className="rounded-2xl min-h-[120px] bg-surface border-border-soft shadow-sm p-4 text-sm leading-relaxed"
                />
              </div>

              <Button 
                className="w-full h-12 rounded-2xl font-bold shadow-lg shadow-accent-teal/20 bg-accent-teal hover:bg-accent-teal/90 text-white" 
                onClick={() => submitMutation.mutate({ severity, symptom_codes: selectedSymptoms.map(s => s.toLowerCase()), free_text: freeText.trim() || undefined, context: {} })}
                disabled={submitMutation.isPending}
              >
                <AsyncLabel active={submitMutation.isPending} loading="Recording" idle="Log Symptom Check-In" />
              </Button>
            </div>
          </div>

          <div className="space-y-6">
            <div className="flex items-center gap-2 px-1">
              <History className="h-4 w-4 text-accent-teal" />
              <h4 className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground">Historical Records</h4>
            </div>
            <div className="grid gap-4">
              {checkIns.slice(0, 5).map((item) => (
                <div key={item.id} className="bg-panel border border-border-soft rounded-2xl p-5 shadow-sm group hover:border-accent-teal/30 transition-all">
                  <div className="flex items-center justify-between text-left">
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-xl border shadow-sm",
                        item.severity >= 4 ? "bg-rose-50 text-rose-600 border-rose-100" : "bg-emerald-50 text-emerald-600 border-emerald-100"
                      )}>
                        <Thermometer className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="text-sm font-bold tracking-tight text-foreground">Severity {item.severity}</div>
                        <div className="text-micro-label font-medium text-muted-foreground opacity-60">
                          {new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.recorded_at))}
                        </div>
                      </div>
                    </div>
                    <Badge 
                      variant="outline"
                      className={cn(
                        "text-[10px] font-bold uppercase tracking-widest px-2.5",
                        item.safety.decision === "escalate" ? "bg-rose-50 text-rose-600 border-rose-100" : "bg-surface text-muted-foreground border-border-soft"
                      )}
                    >
                      {item.safety.decision}
                    </Badge>
                  </div>
                  {item.free_text && (
                    <p className="mt-4 text-xs text-muted-foreground leading-relaxed italic border-l-4 border-accent-teal/20 pl-4">&quot;{item.free_text}&quot;</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <aside className="col-span-12 lg:col-span-4 space-y-10 lg:sticky lg:top-28">
          <div className="bg-panel border border-border-soft rounded-3xl p-8 shadow-sm">
            <div className="flex items-center gap-2 text-accent-teal mb-6">
              <Info className="h-4 w-4" />
              <span className="text-micro-label font-bold uppercase tracking-widest">Aggregate Insights</span>
            </div>
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-1">
                <div className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground opacity-60">Total Logs</div>
                <div className="text-2xl font-bold text-foreground">{summary?.total_count ?? 0}</div>
              </div>
              <div className="space-y-1">
                <div className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground opacity-60">Avg Intensity</div>
                <div className="text-2xl font-bold text-foreground">{(summary?.average_severity ?? 0).toFixed(1)}</div>
              </div>
            </div>
            {summary?.red_flag_count ? (
              <div className="mt-8 rounded-2xl bg-rose-50 p-4 border border-rose-100 flex items-center gap-4 animate-pulse">
                <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0" />
                <span className="text-xs font-bold text-rose-700">{summary.red_flag_count} Critical Red Flags Detected</span>
              </div>
            ) : null}
          </div>

          <div className="space-y-6">
            <div className="flex items-center gap-2 px-1">
              <Activity className="h-4 w-4 text-accent-teal" />
              <h4 className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground">Prevalent Signals</h4>
            </div>
            <div className="flex flex-wrap gap-3">
              {summary?.top_symptoms.map((s) => (
                <div key={s.code} className="flex items-center gap-3 px-4 py-2 rounded-xl border border-border-soft bg-surface text-xs font-bold shadow-sm group hover:border-accent-teal/30 transition-all">
                  <span className="capitalize text-foreground">{s.code}</span>
                  <span className="text-[10px] font-bold text-accent-teal bg-accent-teal-muted px-2 py-0.5 rounded-lg border border-accent-teal/10">{s.count}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
