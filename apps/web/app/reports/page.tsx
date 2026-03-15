"use client";

import { useState } from "react";
import { FileText, Activity, AlertCircle, Calendar, Microscope, ShieldCheck } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { parseReport } from "@/lib/api/meal-client";
import type { ReportParseApiResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

const DEFAULT_REPORT_TEXT = "HbA1c 7.1 LDL 4.2 systolic bp 150 diastolic bp 95";

export default function ReportsPage() {
  const [text, setText] = useState(DEFAULT_REPORT_TEXT);
  const [result, setResult] = useState<ReportParseApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleParse = async () => {
    setError(null);
    setLoading(true);
    try {
      const response = await parseReport({
        source: "pasted_text",
        text: text.trim(),
      });
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="section-stack">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Clinical Intelligence</h1>
        <p className="text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl text-sm">
          Ingest clinical reports, lab results, and diagnostic notes to align your AI companion with your formal medical records.
        </p>
      </div>

      {error && <ErrorCard message={error} />}

      <div className="page-grid items-start">
        <div className="space-y-8">
          <div className="clinical-card space-y-8">
            <div className="space-y-1">
              <h3 className="clinical-subtitle">Report Intake</h3>
              <p className="clinical-body">Paste clinical text or lab results for normalization.</p>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="report-text" className="text-[10px] font-bold uppercase tracking-widest opacity-70">Lab Data / Clinical Notes</Label>
                <Textarea
                  id="report-text"
                  rows={8}
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  placeholder="HbA1c, Blood Pressure, Lipid Profile data..."
                  className="rounded-xl border-2 border-[color:var(--border-soft)] focus:border-[color:var(--accent)]"
                />
              </div>
              <Button
                className="w-full h-12 rounded-xl font-bold shadow-sm"
                disabled={loading || !text.trim()}
                onClick={handleParse}
              >
                <AsyncLabel active={loading} loading="Analyzing" idle="Process Medical Record" />
              </Button>
            </div>
          </div>

          {result && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex items-center gap-2">
                <Microscope className="h-4 w-4 text-[color:var(--muted-foreground)]" />
                <h4 className="text-xs font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Extracted Snapshot</h4>
              </div>
              
              <div className="grid gap-4 sm:grid-cols-2">
                {Object.entries(result.snapshot.biomarkers).map(([name, value]) => (
                  <div key={name} className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 flex items-center justify-between shadow-sm">
                    <div className="space-y-1">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-70">{name}</div>
                      <div className="text-lg font-bold">{String(value)}</div>
                    </div>
                    <div className="h-10 w-10 rounded-lg bg-[color:var(--accent)]/5 flex items-center justify-center text-[color:var(--accent)]">
                      <Activity className="h-5 w-5" />
                    </div>
                  </div>
                ))}
              </div>

              {result.snapshot.risk_flags.length > 0 && (
                <div className="space-y-3">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-rose-600 opacity-70">Identified Risk Flags</div>
                  <div className="flex flex-wrap gap-2">
                    {result.snapshot.risk_flags.map((flag) => (
                      <Badge 
                        key={flag} 
                        variant="outline" 
                        className="rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-tighter bg-rose-50 text-rose-600 border-rose-200"
                      >
                        {flag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="space-y-8 lg:sticky lg:top-28">
          <div className="clinical-card bg-emerald-500/[0.03] border-emerald-500/10">
            <div className="flex items-center gap-2 text-emerald-600 mb-4">
              <ShieldCheck className="h-4 w-4" />
              <span className="text-[10px] font-bold uppercase tracking-widest">Trust & Provenance</span>
            </div>
            <p className="text-xs leading-relaxed text-emerald-800/70">
              Biomarkers are extracted using our validated clinical parser. These signals directly inform your AI assistant&apos;s risk modeling and dietary recommendations.
            </p>
          </div>

          {result && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-[color:var(--muted-foreground)]" />
                <h4 className="text-xs font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Report Context</h4>
              </div>
              <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-5 space-y-4">
                <div className="space-y-1">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-70">Symptom Window</div>
                  <div className="text-xs font-medium">{result.symptom_window.from} — {result.symptom_window.to}</div>
                </div>
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="space-y-1">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-70">Check-ins</div>
                    <div className="text-lg font-bold">{result.symptom_summary.total_count}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-rose-600 opacity-70">Red Flags</div>
                    <div className="text-lg font-bold text-rose-600">{result.symptom_summary.red_flag_count}</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
