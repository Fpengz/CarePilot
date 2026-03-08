"use client";

import { useEffect, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { generateClinicalCard, getClinicalCard, listClinicalCards } from "@/lib/api/meal-client";
import type { ClinicalCardApi } from "@/lib/types";

type LoadingAction = "generate" | "list" | "loadCard" | null;

function dateString(value: Date): string {
  return value.toISOString().slice(0, 10);
}

export default function ClinicalCardsPage() {
  const defaultEnd = dateString(new Date());
  const defaultStart = dateString(new Date(Date.now() - 6 * 24 * 60 * 60 * 1000));
  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(defaultEnd);
  const [format, setFormat] = useState<"sectioned" | "soap">("sectioned");
  const [items, setItems] = useState<ClinicalCardApi[]>([]);
  const [selectedCard, setSelectedCard] = useState<ClinicalCardApi | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<LoadingAction>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoadingAction("list");
        const response = await listClinicalCards(20);
        if (cancelled) return;
        setItems(response.items);
        if (response.items[0]) setSelectedCard(response.items[0]);
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
        eyebrow="Clinical"
        title="Clinical Card Generator"
        description="Generate clinician-ready summary cards with structured sections, deltas, and trend annotations."
        tags={["sectioned summary", "soap", "trend deltas"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Generate Card</CardTitle>
            <CardDescription>Calls `POST /api/v1/clinical-cards/generate` and persists the resulting clinical card.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="clinical-start-date">Start date</Label>
                <Input
                  id="clinical-start-date"
                  type="date"
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="clinical-end-date">End date</Label>
                <Input
                  id="clinical-end-date"
                  type="date"
                  value={endDate}
                  onChange={(event) => setEndDate(event.target.value)}
                />
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="clinical-format">Format</Label>
                <Select
                  id="clinical-format"
                  value={format}
                  onChange={(event) => setFormat(event.target.value as "sectioned" | "soap")}
                >
                  <option value="sectioned">Sectioned</option>
                  <option value="soap">SOAP</option>
                </Select>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                disabled={loadingAction !== null}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("generate");
                  try {
                    const response = await generateClinicalCard({
                      start_date: startDate || undefined,
                      end_date: endDate || undefined,
                      format,
                    });
                    setSelectedCard(response.card);
                    const listResponse = await listClinicalCards(20);
                    setItems(listResponse.items);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "generate"} loading="Generating" idle="Generate Card" />
              </Button>
              <Button
                variant="secondary"
                disabled={loadingAction !== null}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("list");
                  try {
                    const response = await listClinicalCards(20);
                    setItems(response.items);
                    if (response.items[0]) setSelectedCard(response.items[0]);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "list"} loading="Refreshing" idle="Refresh Cards" />
              </Button>
            </div>

            <div className="space-y-2">
              <div className="text-sm font-semibold">Recent cards</div>
              {items.length > 0 ? (
                <div className="data-list">
                  {items.slice(0, 10).map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className={[
                        "w-full rounded-xl border px-3 py-3 text-left transition",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring)] focus-visible:ring-offset-2",
                        "focus-visible:ring-offset-[color:var(--background)]",
                        selectedCard?.id === item.id
                          ? "border-[color:var(--accent)]/40 bg-[color:var(--accent)]/10"
                          : "border-[color:var(--border)] bg-white/60 hover:bg-white/80 dark:bg-[color:var(--panel-soft)] dark:hover:bg-[color:var(--card)]",
                      ].join(" ")}
                      onClick={async () => {
                        setError(null);
                        setLoadingAction("loadCard");
                        try {
                          const response = await getClinicalCard(item.id);
                          setSelectedCard(response.card);
                        } catch (e) {
                          setError(e instanceof Error ? e.message : String(e));
                        } finally {
                          setLoadingAction(null);
                        }
                      }}
                    >
                      <div className="text-sm font-medium">{item.id}</div>
                      <div className="app-muted mt-1 text-xs">
                        {item.start_date} to {item.end_date} • {item.format}
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">No clinical cards generated yet.</p>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}
          <Card>
            <CardHeader>
              <CardTitle>Selected Card Sections</CardTitle>
              <CardDescription>Subjective, objective, assessment, and plan content for clinician review.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {selectedCard ? (
                Object.entries(selectedCard.sections).map(([section, text]) => (
                  <div key={section} className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]">
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">{section}</div>
                    <p className="mt-1 text-sm">{text}</p>
                  </div>
                ))
              ) : (
                <p className="app-muted text-sm">Generate or select a card to inspect sections.</p>
              )}
            </CardContent>
          </Card>
          <JsonViewer
            title="Card Deltas and Trends"
            description="Numerical change analysis and trend metadata attached to the selected card."
            data={selectedCard ? { deltas: selectedCard.deltas, trends: selectedCard.trends } : null}
            emptyLabel="No clinical card selected."
          />
          <JsonViewer
            title="Card Provenance"
            description="Data-source counts used to construct the card."
            data={selectedCard?.provenance ?? null}
            emptyLabel="No provenance data yet."
          />
        </div>
      </div>
    </div>
  );
}
