"use client";

import { useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { PageTitle } from "@/components/app/page-title";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { parseReport } from "@/lib/api/meal-client";
import type { ReportParseApiResponse } from "@/lib/types";

const DEFAULT_REPORT_TEXT = "HbA1c 7.1 LDL 4.2 systolic bp 150 diastolic bp 95";

export default function ReportsPage() {
  const [text, setText] = useState(DEFAULT_REPORT_TEXT);
  const [result, setResult] = useState<ReportParseApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div>
      <PageTitle
        eyebrow="Reports"
        title="Clinical Report Parser"
        description="Paste a clinical report to extract biomarkers and generate targeted health recommendations."
        tags={["biomarkers"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Parse Report Text</CardTitle>
            <CardDescription>Extracts biomarkers, risk flags, and symptom context from pasted lab or clinical text.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="report-text">Report text</Label>
              <Textarea
                id="report-text"
                rows={8}
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="Paste report text here..."
              />
            </div>
            <Button
              disabled={loading || !text.trim()}
              onClick={async () => {
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
              }}
            >
              <AsyncLabel active={loading} loading="Parsing" idle="Parse Report" />
            </Button>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Parsed Biomarkers</CardTitle>
              <CardDescription>Numeric biomarkers extracted from the report payload.</CardDescription>
            </CardHeader>
            <CardContent>
              {result && Object.keys(result.snapshot.biomarkers).length > 0 ? (
                <div className="data-list">
                  {Object.entries(result.snapshot.biomarkers).map(([name, value]) => (
                    <div key={name} className="data-list-row sm:flex-row sm:items-center sm:justify-between">
                      <div className="text-sm font-medium">{name}</div>
                      <div className="text-sm">{value}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">Parse a report to view extracted biomarkers.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Risk and Symptom Summary</CardTitle>
              <CardDescription>Current risk flags and symptom check-in aggregate for the report window.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="text-sm font-semibold">Risk flags</div>
                {result?.snapshot.risk_flags.length ? (
                  <div className="flex flex-wrap gap-2">
                    {result.snapshot.risk_flags.map((flag) => (
                      <Badge key={flag} variant="outline">
                        {flag}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="app-muted text-sm">No risk flags detected.</p>
                )}
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Symptom count</div>
                  <div className="mt-1 text-xl font-semibold">{result?.symptom_summary.total_count ?? 0}</div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Red flags</div>
                  <div className="mt-1 text-xl font-semibold">{result?.symptom_summary.red_flag_count ?? 0}</div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Average severity</div>
                  <div className="mt-1 text-xl font-semibold">{(result?.symptom_summary.average_severity ?? 0).toFixed(2)}</div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Window</div>
                  <div className="mt-1 text-sm font-semibold">
                    {result ? `${result.symptom_window.from} to ${result.symptom_window.to}` : "No window"}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <JsonViewer
            title="Parse Response"
            description="Raw response payload returned by the reports endpoint."
            data={result}
            emptyLabel="Parse a report to inspect payload details."
          />
        </div>
      </div>
    </div>
  );
}
