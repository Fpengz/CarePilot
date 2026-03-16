"use client";

import { useEffect, useState } from "react";
import { FileHeart, ShieldAlert, History, Link as LinkIcon, RefreshCcw, UserCircle, Download } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getClinicianDigest } from "@/lib/api/companion-client";
import type { ClinicianDigestApi } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function ClinicianDigestPage() {
  const [digest, setDigest] = useState<ClinicianDigestApi | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function refresh() {
    setError(null);
    setLoading(true);
    try {
      const response = await getClinicianDigest();
      setDigest(response.digest);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <div className="section-stack max-w-5xl mx-auto">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Clinician Consultation Digest</h1>
          <p className="text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl text-sm">
            A prioritized summary of your longitudinal health data, prepared for clinical review during your next appointment.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={refresh} className="gap-2 rounded-lg">
            <RefreshCcw className="h-3.5 w-3.5" /> Refresh
          </Button>
          <Button variant="default" size="sm" className="gap-2 rounded-lg">
            <Download className="h-3.5 w-3.5" /> Export PDF
          </Button>
        </div>
      </div>

      {error && <ErrorCard message={error} />}

      <div className="grid gap-8 lg:grid-cols-[1fr_300px] lg:items-stretch">
        <div className="space-y-8">
          {/* Main Document Section */}
          <div className="clinical-panel bg-white dark:bg-slate-900 shadow-xl border-[color:var(--border-soft)] p-10 space-y-10">
            {/* Header / Meta */}
            <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between border-b border-[color:var(--border-soft)] pb-8">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                    <UserCircle className="h-8 w-8" />
                  </div>
                  <div>
                    <div className="text-sm font-bold tracking-tight">Patient Digest</div>
                    <div className="text-xs text-[color:var(--muted-foreground)] uppercase tracking-widest font-bold opacity-60">ID: DG-99283-X</div>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Evaluation Window</div>
                  <div className="text-sm font-medium">{digest?.time_window ?? "Last 30 days"}</div>
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <Badge 
                  variant="outline" 
                  className={cn(
                    "px-4 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest",
                    digest?.risk_level === "high" ? "bg-rose-50 text-rose-600 border-rose-200" : ""
                  )}
                >
                  Risk Level: {digest?.risk_level ?? "Low"}
                </Badge>
                <div className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Priority: {digest?.priority ?? "Normal"}</div>
              </div>
            </div>

            {/* Why Now / Summary */}
            <div className="space-y-6">
              <div className="space-y-2">
                <h3 className="text-lg font-bold tracking-tight flex items-center gap-2">
                  <ShieldAlert className="h-5 w-5 text-rose-500" />
                  Clinical Takeaway
                </h3>
                <p className="text-base leading-relaxed text-[color:var(--foreground)] font-medium bg-slate-50 dark:bg-slate-800/50 p-6 rounded-2xl border border-slate-100 dark:border-slate-800">
                  {digest?.summary ?? "Aggregating clinical signals..."}
                </p>
              </div>

              <div className="space-y-2">
                <div className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)] opacity-70">Escalation Context</div>
                <p className="text-sm leading-relaxed italic border-l-4 border-[color:var(--accent)]/30 pl-6 py-2">
                  {digest?.why_now ?? "No immediate escalation triggers detected."}
                </p>
              </div>
            </div>

            {/* Changes / Interventions */}
            <div className="grid gap-10 sm:grid-cols-2">
              <div className="space-y-4">
                <h4 className="text-sm font-bold uppercase tracking-widest text-[color:var(--muted-foreground)] pb-2 border-b border-[color:var(--border-soft)]">
                  Clinical Observations
                </h4>
                <ul className="space-y-4">
                  {digest?.what_changed.map((item, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm leading-relaxed">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-300" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="space-y-4">
                <h4 className="text-sm font-bold uppercase tracking-widest text-[color:var(--muted-foreground)] pb-2 border-b border-[color:var(--border-soft)]">
                  Attempted Interventions
                </h4>
                <ul className="space-y-4">
                  {digest?.interventions_attempted.map((item, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar / Evidence */}
        <div className="flex flex-col h-full">
          <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 flex flex-col h-full">
            <div className="flex items-center gap-2 pb-3 border-b border-[color:var(--border-soft)]">
              <History className="h-4 w-4 text-[color:var(--muted-foreground)]" />
              <h4 className="text-xs font-bold uppercase tracking-widest text-[color:var(--muted-foreground)] opacity-70">Supporting Evidence</h4>
            </div>
            <div className="mt-4 flex-1 min-h-0 overflow-y-auto pr-1 space-y-4">
              {digest?.citations.map((cite, i) => (
                <div key={i} className="group rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 transition-all hover:border-[color:var(--accent)] hover:shadow-sm">
                  <div className="flex items-center gap-2 mb-2">
                    <LinkIcon className="h-3 w-3 text-[color:var(--accent)]" />
                    <span className="text-[10px] font-bold uppercase tracking-tighter text-[color:var(--accent)]">
                      Supporting Evidence
                    </span>
                  </div>
                  {cite.url ? (
                    <a
                      href={cite.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs font-bold leading-snug group-hover:text-[color:var(--accent)] transition-colors"
                    >
                      {cite.title}
                    </a>
                  ) : (
                    <div className="text-xs font-bold leading-snug group-hover:text-[color:var(--accent)] transition-colors">{cite.title}</div>
                  )}
                  <p className="mt-2 text-[10px] leading-relaxed text-[color:var(--muted-foreground)] line-clamp-3 opacity-80">{cite.summary}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
