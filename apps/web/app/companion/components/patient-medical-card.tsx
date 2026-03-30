"use client";

import ReactMarkdown from "react-markdown";
import Link from "next/link";
import { Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { PatientMedicalCardApi } from "@/lib/types";
import { memo } from "react";

interface PatientMedicalCardProps {
  card: PatientMedicalCardApi | null | undefined;
  showFullLink?: boolean;
  loading?: boolean;
}

function PatientMedicalCardBase({ card, showFullLink = false, loading = false }: PatientMedicalCardProps) {
  const markdown = card?.markdown ?? "";
  const generatedLabel = card?.generated_at
    ? new Date(card.generated_at).toLocaleString()
    : "Live Summary";

  return (
    <div className="bg-panel border border-border-soft rounded-3xl overflow-hidden h-[520px] flex flex-col shadow-sm">
      <div className="flex items-center justify-between px-6 py-5 border-b border-border-soft bg-panel/50">
        <div className="min-w-0">
          <div className="text-sm font-bold text-foreground">Patient Medical Card</div>
          <div className="text-micro-label font-bold text-muted-foreground uppercase tracking-widest truncate">
            {generatedLabel}
          </div>
        </div>
        {showFullLink ? (
          <Button asChild variant="secondary" size="sm" className="h-9 rounded-xl px-4 text-xs">
            <Link href="/companion/patient-card">View Full History</Link>
          </Button>
        ) : null}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-4 custom-scrollbar">
        {card?.markdown ? (
          <div className="chat-markdown prose prose-slate dark:prose-invert max-w-none prose-sm prose-headings:text-foreground prose-headings:font-display prose-headings:font-bold prose-p:text-muted-foreground prose-p:leading-relaxed break-words">
            <ReactMarkdown>{markdown}</ReactMarkdown>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-16 text-center h-full bg-surface/50 rounded-2xl border border-dashed border-border-soft">
            <div className="h-12 w-12 rounded-2xl bg-panel border border-border-soft flex items-center justify-center mb-3">
               <Activity className="h-6 w-6 text-muted-foreground opacity-20" />
            </div>
            <p className="text-sm text-muted-foreground italic">
              {loading ? "Generating patient card..." : "No clinical summary available."}
            </p>
          </div>
        )}
      </div>

      {card?.generated_at && (
        <div className="px-6 py-4 border-t border-border-soft bg-panel/50 shrink-0">
          <span className="text-micro-label font-bold text-muted-foreground uppercase tracking-widest">
            Provenance: Clinical Snapshot v2.1
          </span>
        </div>
      )}
    </div>
  );
}

export const PatientMedicalCard = memo(
  PatientMedicalCardBase,
  (prev, next) =>
    prev.showFullLink === next.showFullLink &&
    (prev.card?.markdown ?? "") === (next.card?.markdown ?? "") &&
    (prev.card?.generated_at ?? "") === (next.card?.generated_at ?? "")
);
