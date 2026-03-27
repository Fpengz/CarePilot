"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { ClipboardList, Link as LinkIcon, History } from "lucide-react";

import { ErrorCard } from "@/components/app/error-card";
import { Button } from "@/components/ui/button";
import { getPatientMedicalCard } from "@/lib/api/companion-client";
import type { PatientMedicalCardApi } from "@/lib/types";

export default function PatientCardPage() {
  const [card, setCard] = useState<PatientMedicalCardApi | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const statusLabel = loading
    ? "Refreshing"
    : card?.generated_at
      ? "Ready"
      : "Pending";

  const statusClass = loading
    ? "status-chip status-chip-amber"
    : card?.generated_at
      ? "status-chip status-chip-teal"
      : "status-chip status-chip-slate";

  async function load() {
    setError(null);
    setLoading(true);
    try {
      const response = await getPatientMedicalCard();
      setCard(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="section-stack max-w-5xl mx-auto">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Patient Medical Card</h1>
          <p className="text-sm text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl">
            A focused, patient-friendly summary of recent blood pressure signals and guidance.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={load} className="gap-2 rounded-lg">
          {loading ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      {error ? <ErrorCard message={error} /> : null}

      <div className="grid gap-8 lg:grid-cols-[1fr_300px] lg:items-stretch">
        <div className="flex flex-col h-full">
          <div className="clinical-panel p-10 space-y-8 h-full flex flex-col">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between border-b border-[color:var(--border-soft)] pb-6">
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[color:var(--panel-soft)] text-[color:var(--muted-foreground)]">
                    <ClipboardList className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-sm font-bold tracking-tight">Patient Medical Card</div>
                    <div className="text-[10px] uppercase tracking-widest font-bold text-[color:var(--muted-foreground)] opacity-60">
                      Companion Summary
                    </div>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                    Generated
                  </div>
                  <div className="text-sm font-medium">
                    {card?.generated_at
                      ? new Date(card.generated_at).toLocaleString()
                      : loading
                        ? "Generating summary..."
                        : "Not generated yet"}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 pt-2">
                    <span className={statusClass}>{statusLabel}</span>
                    <span className="status-chip status-chip-slate">On demand</span>
                  </div>
                </div>
              </div>
              <div className="text-[10px] uppercase tracking-widest font-bold text-[color:var(--muted-foreground)]">
                Evidence-Backed Guidance
              </div>
            </div>

            {card?.markdown ? (
              <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-6 flex-1 min-h-0 overflow-y-auto">
                <div className="chat-markdown prose prose-slate dark:prose-invert max-w-none text-sm leading-relaxed">
                  <ReactMarkdown>
                    {card.markdown}
                  </ReactMarkdown>
                </div>
              </div>
            ) : (
              <p className="app-muted text-sm">
                {loading ? "Generating patient card..." : "No patient card available yet."}
              </p>
            )}
          </div>
        </div>

        <div className="flex flex-col h-full">
          <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 flex flex-col h-full">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-[color:var(--muted-foreground)]" />
              <h4 className="text-xs font-bold uppercase tracking-widest text-[color:var(--muted-foreground)] opacity-70">
                Supporting Evidence
              </h4>
            </div>
            <div className="mt-4 flex-1 min-h-0 overflow-y-auto pr-1 space-y-4">
              {card?.citations?.length ? (
                card.citations.map((cite, index) => (
                  <div
                    key={`${cite.title}-${index}`}
                    className="group rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 transition-all hover:border-[color:var(--accent)] hover:shadow-sm"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <LinkIcon className="h-3 w-3 text-[color:var(--accent)]" />
                      <span className="text-[10px] font-bold uppercase tracking-tighter text-[color:var(--accent)]">
                        {cite.relevance}
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
                      <div className="text-xs font-bold leading-snug">{cite.title}</div>
                    )}
                    <p className="mt-2 text-[10px] leading-relaxed text-[color:var(--muted-foreground)] line-clamp-3 opacity-80">
                      {cite.summary}
                    </p>
                  </div>
                ))
              ) : (
                <p className="app-muted text-sm">No supporting evidence yet.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
