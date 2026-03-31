"use client";

import { LayoutDashboard, RefreshCcw, Sparkles } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { useClinicalCards } from "./hooks/use-clinical-cards";
import { cn } from "@/lib/utils";

export default function ClinicalCardsPage() {
  const {
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    format,
    setFormat,
    cards,
    selectedCard,
    selectedCardId,
    setSelectedCardId,
    error,
    loading,
    isGenerating,
    generateCard,
    refresh,
  } = useClinicalCards();

  return (
    <main className="section-stack max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pb-12 bg-background min-h-screen relative isolate">
      <div className="dashboard-grounding" aria-hidden="true" />
      
      <header className="flex flex-col gap-2 py-10">
        <div className="flex items-center gap-3">
          <LayoutDashboard className="h-8 w-8 text-accent-teal" aria-hidden="true" />
          <h1 className="text-h1 font-display tracking-tight text-foreground">Clinical Summaries</h1>
        </div>
        <p className="text-muted-foreground leading-relaxed max-w-2xl text-sm font-medium">
          Generate clinician-ready cards with structured sections, longitudinal deltas, and trend annotations.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
        <div className="lg:col-span-4 space-y-8 lg:sticky lg:top-28">
          <section 
            className="bg-panel border border-border-soft rounded-2xl p-8 shadow-sm space-y-8"
            aria-labelledby="generate-heading"
          >
            <div className="space-y-1">
              <h2 id="generate-heading" className="text-lg font-semibold tracking-tight text-foreground">Configuration</h2>
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-accent-teal">Clinical Controls</p>
            </div>

            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="clinical-start-date" className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">Start date</Label>
                  <Input
                    id="clinical-start-date"
                    type="date"
                    value={startDate}
                    onChange={(event) => setStartDate(event.target.value)}
                    className="rounded-xl border-border-soft bg-surface"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="clinical-end-date" className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">End date</Label>
                  <Input
                    id="clinical-end-date"
                    type="date"
                    value={endDate}
                    onChange={(event) => setEndDate(event.target.value)}
                    className="rounded-xl border-border-soft bg-surface"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="clinical-format" className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">Summary Format</Label>
                <Select
                  id="clinical-format"
                  value={format}
                  onChange={(event) => setFormat(event.target.value as "sectioned" | "soap")}
                  className="rounded-xl border-border-soft bg-surface"
                >
                  <option value="sectioned">Sectioned Overview</option>
                  <option value="soap">SOAP Narrative</option>
                </Select>
              </div>

              <div className="flex flex-col gap-3 pt-2">
                <Button
                  className="h-12 rounded-xl font-bold shadow-sm gap-2"
                  disabled={loading}
                  onClick={generateCard}
                >
                  <Sparkles className="h-4 w-4" aria-hidden="true" />
                  <AsyncLabel active={isGenerating} loading="Synthesizing" idle="Generate Clinical Card" />
                </Button>
                <Button
                  variant="secondary"
                  className="h-12 rounded-xl font-semibold gap-2"
                  disabled={loading}
                  onClick={refresh}
                >
                  <RefreshCcw className={cn("h-4 w-4", loading && !isGenerating && "animate-spin")} aria-hidden="true" />
                  Refresh History
                </Button>
              </div>
            </div>

            <div className="space-y-4 pt-4 border-t border-border-soft">
              <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground opacity-60 px-1">Recent Summaries</h3>
              {cards.length > 0 ? (
                <div className="grid gap-2.5">
                  {cards.slice(0, 10).map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className={cn(
                        "w-full rounded-xl border p-4 text-left transition-all shadow-sm",
                        selectedCardId === item.id || (!selectedCardId && selectedCard?.id === item.id)
                          ? "border-accent-teal bg-accent-teal/5 ring-1 ring-accent-teal/10"
                          : "border-border-soft bg-surface hover:bg-panel"
                      )}
                      onClick={() => setSelectedCardId(item.id)}
                    >
                      <div className="text-[13px] font-bold text-foreground truncate">{item.id}</div>
                      <div className="mt-1 text-[10px] font-bold text-muted-foreground uppercase opacity-60">
                        {item.start_date} — {item.end_date} · {item.format}
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-[12px] text-muted-foreground font-medium italic opacity-60 px-1">No clinical summaries generated.</p>
              )}
            </div>
          </section>
        </div>

        <div className="lg:col-span-8 space-y-12">
          {error && (
            <div role="alert">
              <ErrorCard message={error} />
            </div>
          )}

          <section 
            className="bg-panel border border-border-soft rounded-2xl p-8 shadow-sm"
            aria-labelledby="sections-heading"
          >
            <div className="mb-8 px-1">
              <h2 id="sections-heading" className="text-xl font-semibold tracking-tight text-foreground">Summary Analysis</h2>
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-accent-teal">Clinician Preview</p>
            </div>

            <div className="space-y-6">
              {selectedCard ? (
                Object.entries(selectedCard.sections).map(([section, text]) => (
                  <article key={section} className="space-y-2 px-1">
                    <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground opacity-60">{section}</h3>
                    <p className="text-[14px] leading-relaxed text-foreground font-medium bg-surface/50 p-5 rounded-xl border border-border-soft/50">
                      {text}
                    </p>
                  </article>
                ))
              ) : (
                <div className="py-24 text-center bg-surface/30 border border-dashed border-border-soft rounded-2xl">
                  <p className="text-[13px] text-muted-foreground font-medium italic opacity-60">
                    Select or generate a summary to begin clinical review.
                  </p>
                </div>
              )}
            </div>
          </section>

          <div className="grid gap-8 sm:grid-cols-2">
            <JsonViewer
              title="Deltas & Rhythms"
              description="Longitudinal change analysis."
              data={selectedCard ? { deltas: selectedCard.deltas, trends: selectedCard.trends } : null}
              emptyLabel="No analysis data."
            />
            <JsonViewer
              title="Data Provenance"
              description="Source signals used for synthesis."
              data={selectedCard?.provenance ?? null}
              emptyLabel="No provenance data."
            />
          </div>
        </div>
      </div>
    </main>
  );
}
