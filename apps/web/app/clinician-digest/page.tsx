"use client";

import { useEffect, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getClinicianDigest } from "@/lib/api/companion-client";
import type { ClinicianDigestApi } from "@/lib/types";

export default function ClinicianDigestPage() {
  const [digest, setDigest] = useState<ClinicianDigestApi | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function refresh() {
    const response = await getClinicianDigest();
    setDigest(response.digest);
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        const response = await getClinicianDigest();
        if (!cancelled) setDigest(response.digest);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
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
        eyebrow="Clinician"
        title="Clinician Digest"
        description="Compress longitudinal patient behavior into a low-burden summary with why-now context, attempted interventions, and supporting evidence."
        tags={["summary", "prioritization", "provenance"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Current Digest</CardTitle>
            <CardDescription>Calls `GET /api/v1/clinician/digest` and surfaces the prioritized clinical view, not the raw payload.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <Button
                disabled={loading}
                onClick={async () => {
                  setError(null);
                  setLoading(true);
                  try {
                    await refresh();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoading(false);
                  }
                }}
              >
                <AsyncLabel active={loading} idle="Refresh Digest" loading="Refreshing" />
              </Button>
              {digest ? <Badge variant={digest.risk_level === "high" ? "default" : "outline"}>{digest.risk_level}</Badge> : null}
              {digest ? <Badge variant="outline">{digest.priority}</Badge> : null}
            </div>
            <div className="rounded-xl border border-[color:var(--border)] bg-white/70 p-4 dark:bg-[color:var(--panel-soft)]">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Why Now</div>
              <p className="mt-2 text-sm">{digest?.why_now ?? "Loading clinician digest…"}</p>
              <p className="app-muted mt-2 text-xs">{digest?.time_window ?? "No time window yet."}</p>
            </div>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}
          <Card>
            <CardHeader>
              <CardTitle>Summary</CardTitle>
              <CardDescription>The core clinical takeaway the companion wants to surface.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 text-sm dark:bg-[color:var(--panel-soft)]">
                {digest?.summary ?? "No digest summary yet."}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>What Changed</CardTitle>
              <CardDescription>Only the changes likely to matter clinically should appear here.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {digest?.what_changed?.length ? (
                digest.what_changed.map((item) => (
                  <div key={item} className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 text-sm dark:bg-[color:var(--panel-soft)]">
                    {item}
                  </div>
                ))
              ) : (
                <p className="app-muted text-sm">No digest changes available yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Interventions Attempted</CardTitle>
              <CardDescription>Show what the companion has already tried before escalating burden to the clinician.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {digest?.interventions_attempted?.length ? (
                digest.interventions_attempted.map((item) => (
                  <div key={item} className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 text-sm dark:bg-[color:var(--panel-soft)]">
                    {item}
                  </div>
                ))
              ) : (
                <p className="app-muted text-sm">No interventions captured yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Supporting Evidence</CardTitle>
              <CardDescription>The companion attaches evidence notes so the digest is not just a generic summary.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {digest?.citations?.length ? (
                digest.citations.map((item) => (
                  <div key={`${item.title}-${item.relevance}`} className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]">
                    <div className="font-medium">{item.title}</div>
                    <p className="app-muted mt-2 text-sm">{item.summary}</p>
                    <p className="mt-2 text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">{item.relevance}</p>
                  </div>
                ))
              ) : (
                <p className="app-muted text-sm">No evidence attached yet.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
