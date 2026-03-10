"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageTitle } from "@/components/app/page-title";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { listMedicationRegimens } from "@/lib/api/medication-client";
import { getMedicationAdherenceMetrics } from "@/lib/api/medication-client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { MedicationRegimenApi } from "@/lib/types";

export default function MedicationsPage() {
  const { data: regimensResult } = useQuery({
    queryKey: ["medication-regimens"],
    queryFn: listMedicationRegimens,
  });

  const regimens = regimensResult?.items ?? [];

  const { data: metrics } = useQuery({
    queryKey: ["medication-metrics"],
    queryFn: () => getMedicationAdherenceMetrics(),
  });

  return (
    <div>
      <PageTitle
        eyebrow="Care"
        title="Medications & Adherence"
        description="Manage your medication regimens and track adherence history."
        tags={["care plan", "adherence"]}
      />

      <div className="page-grid">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Adherence Metrics</CardTitle>
              <CardDescription>Your medication follow-through over time.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Adherence Rate</div>
                  <div className="mt-1 text-sm font-medium">
                    {metrics?.totals?.adherence_rate != null ? `${Math.round(metrics.totals.adherence_rate * 100)}%` : "—"}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="regimens" className="w-full">
          <TabsList className="mb-4">
            <TabsTrigger value="regimens">Regimens</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>

          <TabsContent value="regimens" className="space-y-4 mt-0">
             {regimens.map((regimen: MedicationRegimenApi) => (
                <Card key={regimen.id}>
                  <CardContent className="pt-6">
                    <div className="font-medium">{regimen.medication_name}</div>
                    <div className="text-sm text-[color:var(--muted-foreground)]">{regimen.dosage_text}</div>
                  </CardContent>
                </Card>
             ))}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
