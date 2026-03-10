"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { EvidenceCitation } from "@/lib/types";

interface SupportingEvidenceCardProps {
  citations: EvidenceCitation[];
}

export function SupportingEvidenceCard({ citations }: SupportingEvidenceCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Supporting Evidence</CardTitle>
        <CardDescription>
          These evidence notes support the current recommendation and clinician-facing summary.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {citations.length ? (
          citations.map((item) => (
            <div
              key={`${item.title}-${item.relevance}`}
              className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="font-medium">{item.title}</div>
                <Badge variant="outline">{Math.round(item.confidence * 100)}%</Badge>
              </div>
              <p className="app-muted mt-2 text-sm">{item.summary}</p>
              <p className="mt-2 text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">
                {item.relevance}
              </p>
            </div>
          ))
        ) : (
          <p className="app-muted text-sm">No supporting evidence yet.</p>
        )}
      </CardContent>
    </Card>
  );
}
