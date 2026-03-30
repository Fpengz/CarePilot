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
    <div className="bg-panel border border-border-soft rounded-3xl overflow-hidden h-[520px] flex flex-col shadow-sm">
      <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-4 custom-scrollbar">
        {citations.length ? (
          citations.map((item, idx) => (
            <div
              key={`${item.title}-${idx}`}
              className="group rounded-2xl border border-border-soft bg-surface p-5 shadow-sm transition-all hover:bg-surface/80"
            >
              <div className="flex items-start justify-between gap-4 min-w-0">
                <div className="flex flex-col gap-2 min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="bg-accent-teal-muted text-accent-teal text-micro-label font-bold uppercase tracking-widest px-2 py-0 border-accent-teal/20">
                      {item.source_type || "Clinical"}
                    </Badge>
                  </div>
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm font-bold leading-tight text-foreground group-hover:text-accent-teal transition-colors break-words"
                    >
                      {item.title}
                    </a>
                  ) : (
                    <span className="text-sm font-bold leading-tight text-foreground break-words">
                      {item.title}
                    </span>
                  )}
                </div>
                <div className="flex flex-col items-end gap-1.5 shrink-0">
                   <div className="text-[11px] font-mono font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-lg border border-emerald-100">
                     {Math.round(item.confidence * 100)}%
                   </div>
                   <span className="text-micro-label uppercase font-bold text-muted-foreground tracking-tight opacity-60">Evidence</span>
                </div>
              </div>
              <p className="mt-4 text-xs leading-relaxed text-muted-foreground font-medium break-words">
                {item.summary}
              </p>
            </div>
          ))
        ) : (
          <div className="flex flex-col items-center justify-center py-16 text-center h-full bg-surface/50 rounded-2xl border border-dashed border-border-soft">
            <BookOpen className="h-10 w-10 text-muted-foreground opacity-20 mb-3" />
            <p className="text-sm text-muted-foreground italic">No citations retrieved for this interaction.</p>
          </div>
        )}
      </div>
      
      {citations.length > 0 && (
        <div className="px-6 py-4 border-t border-border-soft bg-panel/50 shrink-0">
          <span className="text-micro-label font-bold text-muted-foreground uppercase tracking-widest">
            {citations.length} Clinical Documents Cited
          </span>
        </div>
      )}
    </div>
  );
}
