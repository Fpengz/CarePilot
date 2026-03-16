"use client";

import { BookOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { EvidenceCitation } from "@/lib/types";

interface SupportingEvidenceCardProps {
  citations: EvidenceCitation[];
}

export function SupportingEvidenceCard({ citations }: SupportingEvidenceCardProps) {
  return (
    <Card className="p-0 overflow-hidden">
      <CardContent className="p-0 h-full flex flex-col">
      <div className="flex-1 max-h-[420px] overflow-y-auto p-5 space-y-4 custom-scrollbar">
        {citations.length ? (
          citations.map((item, idx) => (
            <div
              key={`${item.title}-${idx}`}
              className="group rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 shadow-sm transition-all hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-3 min-w-0">
                <div className="flex flex-col gap-1.5 min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="bg-[color:var(--accent)]/10 text-[color:var(--accent)] text-[9px] font-bold uppercase tracking-widest px-1.5 py-0 border-[color:var(--accent)]/20">
                      {item.source_type || "Clinical"}
                    </Badge>
                  </div>
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs font-bold leading-snug text-[color:var(--foreground)] group-hover:text-[color:var(--accent)] transition-colors break-words"
                    >
                      {item.title}
                    </a>
                  ) : (
                    <span className="text-xs font-bold leading-snug text-[color:var(--foreground)] break-words">
                      {item.title}
                    </span>
                  )}
                </div>
                <div className="flex flex-col items-end gap-1 shrink-0">
                   <div className="text-[10px] font-mono font-bold text-health-teal bg-health-teal-soft px-1.5 rounded border border-health-teal/20">
                     {Math.round(item.confidence * 100)}%
                   </div>
                   <span className="text-[8px] uppercase font-bold text-[color:var(--muted-foreground)] tracking-tight">Strength</span>
                </div>
              </div>
              <p className="mt-3 text-[11px] leading-relaxed text-[color:var(--muted-foreground)] font-medium break-words">
                {item.summary}
              </p>
            </div>
          ))
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center h-full">
            <BookOpen className="h-8 w-8 text-[color:var(--muted-foreground)]/40 mb-2" />
            <p className="text-xs text-[color:var(--muted-foreground)] italic">No citations retrieved for this interaction.</p>
          </div>
        )}
      </div>
      
      {citations.length > 0 && (
        <div className="px-5 py-3 border-t border-[color:var(--border-soft)] bg-[color:var(--panel-soft)] shrink-0">
          <span className="text-[9px] font-bold text-[color:var(--muted-foreground)] uppercase tracking-widest">
            {citations.length} Clinical Documents Cited
          </span>
        </div>
      )}
      </CardContent>
    </Card>
  );
}
