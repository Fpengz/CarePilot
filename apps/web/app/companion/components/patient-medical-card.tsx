"use client";

import ReactMarkdown from "react-markdown";
import Link from "next/link";
import { Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { PatientMedicalCardApi } from "@/lib/types";
import { memo, useMemo } from "react";

interface PatientMedicalCardProps {
  card: PatientMedicalCardApi | null | undefined;
  showFullLink?: boolean;
  loading?: boolean;
}

function PatientMedicalCardBase({ card, showFullLink = false, loading = false }: PatientMedicalCardProps) {
  const markdown = useMemo(() => card?.markdown ?? "", [card?.markdown]);
  const generatedLabel = useMemo(
    () => (card?.generated_at ? new Date(card.generated_at).toLocaleString() : "Live Summary"),
    [card?.generated_at]
  );

  return (
    <Card className="p-0 overflow-hidden">
      <CardContent className="p-0 h-full flex flex-col">
      <div className="flex items-center justify-between px-5 py-4 border-b border-[color:var(--border-soft)] bg-[color:var(--panel-soft)]">
        <div className="min-w-0">
          <div className="text-sm font-bold text-[color:var(--foreground)]">Patient Medical Card</div>
          <div className="text-[10px] font-bold text-[color:var(--muted-foreground)] uppercase tracking-widest truncate">
            {generatedLabel}
          </div>
        </div>
        {showFullLink ? (
          <Button asChild variant="secondary" size="sm" className="h-9 rounded-lg">
            <Link href="/companion/patient-card">Open full card</Link>
          </Button>
        ) : null}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 max-h-[420px] overflow-y-auto p-5 space-y-4 custom-scrollbar">
        {card?.markdown ? (
          <div className="chat-markdown prose prose-slate max-w-none prose-sm prose-headings:text-[color:var(--foreground)] prose-headings:font-bold prose-p:text-[color:var(--muted-foreground)] prose-p:leading-relaxed break-words">
            <ReactMarkdown>{markdown}</ReactMarkdown>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="h-12 w-12 rounded-full bg-[color:var(--panel-soft)] flex items-center justify-center mb-3">
               <Activity className="h-6 w-6 text-[color:var(--muted-foreground)]/40" />
            </div>
            <p className="text-xs text-[color:var(--muted-foreground)] italic">
              {loading ? "Generating patient card..." : "No clinical summary available."}
            </p>
          </div>
        )}
      </div>

      {card?.generated_at && (
        <div className="px-5 py-3 border-t border-[color:var(--border-soft)] bg-[color:var(--panel-soft)] shrink-0">
          <span className="text-[9px] font-bold text-[color:var(--muted-foreground)] uppercase tracking-widest">
            Last Generated: {generatedLabel}
          </span>
        </div>
      )}
      </CardContent>
    </Card>
  );
}

export const PatientMedicalCard = memo(
  PatientMedicalCardBase,
  (prev, next) =>
    prev.showFullLink === next.showFullLink &&
    (prev.card?.markdown ?? "") === (next.card?.markdown ?? "") &&
    (prev.card?.generated_at ?? "") === (next.card?.generated_at ?? "")
);
