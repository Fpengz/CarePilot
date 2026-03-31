"use client";

import { Activity, AlertTriangle, RefreshCcw, Thermometer, Info, History } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useSymptoms } from "./hooks/use-symptoms";

const COMMON_SYMPTOMS = ["Headache", "Fatigue", "Nausea", "Dizziness", "Bloating", "Thirst"];

export default function SymptomsPage() {
  const {
    severity,
    setSeverity,
    selectedSymptoms,
    toggleSymptom,
    freeText,
    setFreeText,
    error,
    checkIns,
    summary,
    submitting,
    logCheckIn,
    refresh,
  } = useSymptoms();

  return (
    <main className="section-stack max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pb-12 bg-background min-h-screen relative isolate">
      <div className="dashboard-grounding" aria-hidden="true" />
      
      <header className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between py-10">
        <div className="space-y-2">
          <h1 className="text-h1 font-display tracking-tight text-foreground">Symptom Monitoring</h1>
          <p className="text-muted-foreground leading-relaxed max-w-2xl text-sm font-medium">
            Log physical signals to help your AI companion detect patterns and provide safer clinical guidance.
          </p>
        </div>
        <div className="pb-1">
          <Button variant="secondary" size="sm" onClick={refresh} className="gap-2 rounded-xl h-11 px-6 bg-surface shadow-sm border-border-soft hover:bg-panel transition-all">
            <RefreshCcw className="h-4 w-4 text-accent-teal" aria-hidden="true" /> Sync Clinical Data
          </Button>
        </div>
      </header>

      {error && (
        <div className="mb-8" role="alert">
          <ErrorCard message={error} />
        </div>
      )}

      <div className="grid grid-cols-12 gap-12 items-start">
        <div className="col-span-12 lg:col-span-8 space-y-12">
          <section 
            className="bg-panel border border-border-soft rounded-2xl p-8 shadow-sm space-y-10"
            aria-labelledby="checkin-heading"
          >
            <div className="space-y-1.5 px-1">
              <h3 id="checkin-heading" className="text-xl font-semibold tracking-tight text-foreground">Active Check-In</h3>
              <p className="text-sm text-muted-foreground font-medium">How are you feeling right now?</p>
            </div>

            <div className="space-y-10">
              <div className="space-y-4">
                <div className="flex items-center justify-between px-1">
                  <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-accent-teal">Intensity Level</Label>
                  <Badge variant="outline" className={cn(
                    "text-[10px] font-bold uppercase tracking-widest px-3 py-1",
                    severity >= 4 ? "bg-health-rose/10 text-health-rose border-health-rose/20" : "bg-health-teal/10 text-health-teal border-health-teal/20"
                  )}>Level {severity}</Badge>
                </div>
                <div className="flex gap-3">
                  {[1, 2, 3, 4, 5].map((val) => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setSeverity(val)}
                      className={cn(
                        "flex-1 h-12 rounded-xl border-2 transition-all font-bold text-[13px] uppercase tracking-wider",
                        severity === val 
                          ? "border-accent-teal bg-accent-teal text-white shadow-sm scale-[1.02]" 
                          : "border-border-soft bg-surface text-muted-foreground hover:border-accent-teal/30 shadow-sm"
                      )}
                    >
                      {val}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-4">
                <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-accent-teal px-1">Observed Symptoms</Label>
                <div className="flex flex-wrap gap-2.5">
                  {COMMON_SYMPTOMS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => toggleSymptom(s)}
                      className={cn(
                        "rounded-xl border-2 px-5 py-2 text-[11px] font-bold transition-all shadow-sm uppercase tracking-widest",
                        selectedSymptoms.includes(s) 
                          ? "border-accent-teal bg-accent-teal text-white shadow-sm" 
                          : "border-border-soft bg-surface text-muted-foreground hover:border-accent-teal/30"
                      )}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-4">
                <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-accent-teal px-1">Clinical Narrative</Label>
                <Textarea
                  placeholder="e.g., Describe timing, duration, or triggers..."
                  value={freeText}
                  onChange={(e) => setFreeText(e.target.value)}
                  className="rounded-xl min-h-[140px] bg-surface border-border-soft shadow-sm p-5 text-sm leading-relaxed resize-none focus:bg-panel transition-colors"
                />
              </div>

              <Button 
                className="w-full h-12 rounded-xl font-bold shadow-sm" 
                onClick={logCheckIn}
                disabled={submitting}
              >
                <AsyncLabel active={submitting} loading="Recording" idle="Log Symptom Check-In" />
              </Button>
            </div>
          </section>

          <section className="space-y-6">
            <div className="flex items-center gap-2 px-1">
              <History className="h-4 w-4 text-accent-teal" aria-hidden="true" />
              <h4 className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground">Historical Records</h4>
            </div>
            <div className="grid gap-4">
              {checkIns.slice(0, 5).map((item) => (
                <article key={item.id} className="bg-panel border border-border-soft rounded-xl p-5 shadow-sm group hover:border-accent-teal/30 transition-all">
                  <div className="flex items-center justify-between text-left">
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-lg border shadow-sm",
                        item.severity >= 4 ? "bg-health-rose/5 text-health-rose border-health-rose/10" : "bg-health-teal/5 text-health-teal border-health-teal/10"
                      )}>
                        <Thermometer className="h-5 w-5" aria-hidden="true" />
                      </div>
                      <div>
                        <div className="text-[13px] font-bold tracking-tight text-foreground truncate">Severity {item.severity}</div>
                        <div className="text-[10px] font-bold text-muted-foreground opacity-60 uppercase">
                          {new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.recorded_at))}
                        </div>
                      </div>
                    </div>
                    <Badge 
                      variant="outline"
                      className={cn(
                        "text-[9px] font-bold uppercase tracking-widest px-2.5 py-0.5",
                        item.safety.decision === "escalate" ? "bg-health-rose/10 text-health-rose border-health-rose/20" : "bg-surface text-muted-foreground border-border-soft"
                      )}
                    >
                      {item.safety.decision}
                    </Badge>
                  </div>
                  {item.free_text && (
                    <p className="mt-4 text-[12px] text-muted-foreground leading-relaxed italic border-l-2 border-accent-teal/20 pl-4">&quot;{item.free_text}&quot;</p>
                  )}
                </article>
              ))}
            </div>
          </section>
        </div>

        <aside className="col-span-12 lg:col-span-4 space-y-10 lg:sticky lg:top-28">
          <section 
            className="bg-panel border border-border-soft rounded-2xl p-8 shadow-sm space-y-8"
            aria-labelledby="insights-heading"
          >
            <div className="flex items-center gap-2 text-accent-teal">
              <Info className="h-4 w-4" aria-hidden="true" />
              <h3 id="insights-heading" className="text-[10px] font-bold uppercase tracking-[0.2em]">Aggregate Insights</h3>
            </div>
            
            <div className="grid grid-cols-2 gap-8">
              <div className="space-y-1">
                <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground opacity-60">Total Logs</div>
                <div className="text-3xl font-display font-semibold text-foreground">{summary?.total_count ?? 0}</div>
              </div>
              <div className="space-y-1">
                <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground opacity-60">Avg Intensity</div>
                <div className="text-3xl font-display font-semibold text-foreground">{(summary?.average_severity ?? 0).toFixed(1)}</div>
              </div>
            </div>

            {summary?.red_flag_count ? (
              <div 
                className="rounded-xl bg-health-rose/10 p-4 border border-health-rose/20 flex items-center gap-4 animate-in fade-in slide-in-from-bottom-2"
                role="alert"
              >
                <AlertTriangle className="h-5 w-5 text-health-rose shrink-0" aria-hidden="true" />
                <span className="text-[11px] font-bold text-health-rose uppercase tracking-widest leading-tight">
                  {summary.red_flag_count} Critical Red Flags Detected
                </span>
              </div>
            ) : null}
          </section>

          <section className="space-y-6">
            <div className="flex items-center gap-2 px-1">
              <Activity className="h-4 w-4 text-accent-teal" aria-hidden="true" />
              <h4 className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground">Prevalent Signals</h4>
            </div>
            <div className="flex flex-wrap gap-2.5">
              {summary?.top_symptoms.map((s) => (
                <div key={s.code} className="flex items-center gap-3 px-4 py-2 rounded-xl border border-border-soft bg-panel text-[11px] font-bold shadow-sm group hover:border-accent-teal/30 transition-all uppercase tracking-widest">
                  <span className="text-foreground">{s.code}</span>
                  <span className="flex h-5 min-w-5 items-center justify-center rounded-lg bg-accent-teal/10 text-[9px] text-accent-teal font-bold border border-accent-teal/10">{s.count}</span>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </main>
  );
}
