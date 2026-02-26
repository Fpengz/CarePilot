"use client";

import { useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { generateRecommendation, parseReport } from "@/lib/api";

export default function ReportsPage() {
  const [reportText, setReportText] = useState("HbA1c 7.1 LDL 4.2 systolic bp 150 diastolic bp 95");
  const [parseResult, setParseResult] = useState<object | null>(null);
  const [recommendationResult, setRecommendationResult] = useState<object | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<"parse" | "recommend" | null>(null);
  const parseSnapshot = (parseResult as { snapshot?: { biomarkers?: Record<string, number>; risk_flags?: string[] } } | null)
    ?.snapshot;
  const recommendation = (recommendationResult as { recommendation?: Record<string, unknown> } | null)?.recommendation;
  const recommendationEntries = Object.entries(recommendation ?? {}).slice(0, 8);

  return (
    <div>
      <PageTitle
        eyebrow="Reports"
        title="Parse Reports and Generate Recommendations"
        description="Paste report text, inspect parsed biomarker snapshots, and trigger grounded recommendation generation using the new auth model."
        tags={["member scopes", "grounded outputs"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Report Input</CardTitle>
            <CardDescription>
              Uses `POST /api/v1/reports/parse` and `POST /api/v1/recommendations/generate`.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="report-text">Pasted report text</Label>
              <Textarea
                id="report-text"
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
                  setLoadingAction("parse");
                  try {
                    const result = await parseReport({ source: "pasted_text", text: reportText });
                    setParseResult(result);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "parse"} loading="Parsing" idle="Parse Report" />
              </Button>
              <Button
                variant="secondary"
                disabled={loadingAction !== null}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("recommend");
                  try {
                    const result = await generateRecommendation();
                    setRecommendationResult(result);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "recommend"} loading="Generating" idle="Generate Recommendation" />
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Snapshot Preview</CardTitle>
              <CardDescription>Parsed biomarkers and risk flags at a glance.</CardDescription>
            </CardHeader>
            <CardContent>
              {parseSnapshot ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="metric-card sm:col-span-2">
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Risk Flags</div>
                    <div className="mt-1 text-sm font-medium">
                      {(parseSnapshot.risk_flags ?? []).length > 0 ? (parseSnapshot.risk_flags ?? []).join(", ") : "None"}
                    </div>
                  </div>
                  {Object.entries(parseSnapshot.biomarkers ?? {})
                    .slice(0, 4)
                    .map(([key, value]) => (
                      <div key={key} className="metric-card">
                        <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">{key}</div>
                        <div className="mt-1 text-sm font-medium">{value}</div>
                      </div>
                    ))}
                </div>
              ) : (
                <p className="app-muted text-sm">Parse a report to preview structured biomarkers.</p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Recommendation Preview</CardTitle>
              <CardDescription>Structured highlights from the generated recommendation payload.</CardDescription>
            </CardHeader>
            <CardContent>
              {recommendation ? (
                <div className="space-y-3">
                  {recommendationEntries.length > 0 ? (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {recommendationEntries.map(([key, value]) => (
                        <div key={key} className="metric-card">
                          <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">
                            {key.replaceAll("_", " ")}
                          </div>
                          <div className="mt-1 text-sm font-medium break-words">
                            {typeof value === "string" || typeof value === "number" || typeof value === "boolean"
                              ? String(value)
                              : Array.isArray(value)
                                ? `${value.length} item(s)`
                                : "Object"}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  <p className="app-muted text-xs">
                    Raw payload is still available below for debugging and contract inspection.
                  </p>
                </div>
              ) : (
                <p className="app-muted text-sm">Generate a recommendation to preview structured fields.</p>
              )}
            </CardContent>
          </Card>
          <JsonViewer title="Parsed Snapshot" data={parseResult} emptyLabel="Parse a report to inspect the structured snapshot." />
          <JsonViewer
            title="Recommendation"
            data={recommendationResult}
            emptyLabel="Generate a recommendation to inspect the grounded response payload."
          />
        </div>
      </div>
    </div>
  );
}
