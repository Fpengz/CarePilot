"use client";

import { useMemo, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { KeyValuePreview } from "@/components/app/key-value-preview";
import { PageTitle } from "@/components/app/page-title";
import { TimelineList } from "@/components/app/timeline-list";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { generateSuggestionFromReport, getSuggestion, listSuggestions } from "@/lib/api";
import type { SuggestionItemApi } from "@/lib/types";

const DEFAULT_REPORT = "HbA1c 7.1 LDL 4.2 systolic bp 150 diastolic bp 95";

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export default function SuggestionsPage() {
  const [reportText, setReportText] = useState(DEFAULT_REPORT);
  const [selected, setSelected] = useState<SuggestionItemApi | null>(null);
  const [items, setItems] = useState<SuggestionItemApi[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<"generate" | "load" | "open" | null>(null);

  const recommendation = selected?.recommendation;
  const recommendationEntries = useMemo(
    () => Object.entries(recommendation ?? {}).slice(0, 8).map(([key, value]) => ({ key: key.replaceAll("_", " "), value })),
    [recommendation],
  );

  return (
    <div>
      <PageTitle
        eyebrow="Suggestions"
        title="Report-to-Suggestion Workflow"
        description="Generate structured suggestions from pasted report text with one action, then review persisted suggestion history."
        tags={["unified endpoint", "persisted history"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Generate Suggestion</CardTitle>
            <CardDescription>
              Uses `POST /api/v1/suggestions/generate-from-report` and stores a reusable suggestion snapshot.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="suggestions-report-text">Report text</Label>
              <Textarea
                id="suggestions-report-text"
                className="app-code min-h-[180px] bg-[#161714] text-[#ece8dc] placeholder:text-[#b3b7ae]"
                rows={7}
                value={reportText}
                onChange={(e) => setReportText(e.target.value)}
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                disabled={loadingAction !== null || reportText.trim().length === 0}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("generate");
                  try {
                    const response = await generateSuggestionFromReport({ text: reportText });
                    setSelected(response.suggestion);
                    const listResponse = await listSuggestions(20);
                    setItems(listResponse.items);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "generate"} loading="Generating" idle="Generate Suggestion" />
              </Button>

              <Button
                variant="secondary"
                disabled={loadingAction !== null}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("load");
                  try {
                    const response = await listSuggestions(20);
                    setItems(response.items);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "load"} loading="Loading" idle="Load Suggestions" />
              </Button>
            </div>

            {selected ? (
              <div className="metric-card">
                <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Current Suggestion</div>
                <div className="mt-1 text-sm font-medium">{selected.suggestion_id}</div>
                <p className="app-muted mt-2 text-xs">{selected.disclaimer}</p>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}

          <TimelineList
            title="Suggestion History"
            description="Recent saved suggestions for the current account."
            emptyLabel="No suggestions yet. Generate one from report text."
            items={items.map((item) => ({
              id: item.suggestion_id,
              title: item.suggestion_id,
              subtitle: formatDate(item.created_at),
              badges: [String(item.recommendation.safe ? "safe" : "review")],
              onClick: async () => {
                setError(null);
                setLoadingAction("open");
                try {
                  const detail = await getSuggestion(item.suggestion_id);
                  setSelected(detail.suggestion);
                } catch (e) {
                  setError(e instanceof Error ? e.message : String(e));
                } finally {
                  setLoadingAction(null);
                }
              },
            }))}
          />

          <KeyValuePreview
            title="Recommendation Preview"
            description="Top fields from the generated recommendation payload."
            entries={recommendationEntries}
            emptyLabel="Generate or open a suggestion to preview recommendation fields."
          />

          <JsonViewer
            title="Selected Suggestion"
            data={selected}
            emptyLabel="Generate or load suggestions to inspect the full payload."
          />
        </div>
      </div>
    </div>
  );
}
