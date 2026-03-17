"use client";

import { Stethoscope, ClipboardCheck } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ClinicianDigest } from "@/lib/types";

interface ClinicianDigestCardProps {
  digest: ClinicianDigest | undefined;
}

export function ClinicianDigestCard({ digest }: ClinicianDigestCardProps) {
  return (
    <Card className="shadow-sm rounded-xl overflow-hidden h-full flex flex-col">
      <CardHeader className="bg-[color:var(--panel-soft)] border-b border-[color:var(--border-soft)] pb-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-health-teal-soft text-health-teal">
            <Stethoscope className="h-4 w-4" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-[color:var(--foreground)]">Clinician Digest Preview</CardTitle>
            <CardDescription className="text-[10px] font-medium uppercase tracking-tight">Low-Burden Summary for Follow-up</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-6 space-y-6 flex-1 min-h-0">
        <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 shadow-sm">
          <div className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)] mb-2">Executive Summary</div>
          <p className="text-sm font-bold text-[color:var(--foreground)] leading-relaxed">
            {digest?.summary ?? "Awaiting patient interaction to generate clinician-facing briefing."}
          </p>
          <div className="mt-3 pt-3 border-t border-[color:var(--border-soft)]">
             <p className="text-xs text-[color:var(--muted-foreground)] italic">Rationale: {digest?.why_now ?? "Priority status not yet determined."}</p>
          </div>
        </div>

        <div className="space-y-3">
          <div className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Clinical Transitions</div>
          {digest?.what_changed?.length ? (
            <div className="space-y-2">
              {digest.what_changed.slice(0, 3).map((item: string, index: number) => (
                <div
                  key={`${item}-${index}`}
                  className="flex items-center gap-3 p-3 rounded-lg border border-[color:var(--border-soft)] bg-[color:var(--panel-soft)] text-xs font-medium text-[color:var(--muted-foreground)]"
                >
                  <ClipboardCheck className="h-3.5 w-3.5 text-health-teal shrink-0" />
                  {item}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-[color:var(--muted-foreground)] italic">No significant transitions detected.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
