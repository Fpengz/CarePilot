"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ClinicianDigest } from "@/lib/types";

interface ClinicianDigestCardProps {
  digest: ClinicianDigest | undefined;
}

export function ClinicianDigestCard({ digest }: ClinicianDigestCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Clinician Digest Preview</CardTitle>
        <CardDescription>
          Preview the low-burden summary a clinician would see if this needs follow-up.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="clinical-alert">
          <div className="font-medium">{digest?.summary ?? "Run an interaction to preview the digest."}</div>
          <p className="app-muted mt-2">{digest?.why_now ?? "No clinician rationale yet."}</p>
        </div>
        {digest?.what_changed?.slice(0, 3).map((item: string, index: number) => (
          <div
            key={`${item}-${index}`}
            className="clinical-alert"
          >
            {item}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
