"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  confirmMedicationIntake,
  deleteMedicationRegimen,
  getMedicationAdherenceMetrics,
  intakeMedicationFromText,
  intakeMedicationFromUpload,
  listMedicationRegimens,
  updateMedicationRegimen,
} from "@/lib/api/medication-client";
import type {
  MedicationIntakeApiResponse,
} from "@/lib/types";

export function useMedications() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [intakeResult, setIntakeResult] = useState<MedicationIntakeApiResponse | null>(null);

  const { data: regimensResult, isLoading: regimensLoading } = useQuery({
    queryKey: ["medication-regimens"],
    queryFn: listMedicationRegimens,
  });

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ["medication-metrics"],
    queryFn: () => getMedicationAdherenceMetrics(),
  });

  const intakeTextMutation = useMutation({
    mutationFn: (text: string) => intakeMedicationFromText({ instructions_text: text }),
    onSuccess: (result) => {
      setIntakeResult(result);
      setError(null);
    },
    onError: (mutationError) => {
      setError(mutationError instanceof Error ? mutationError.message : String(mutationError));
    },
  });

  const intakeUploadMutation = useMutation({
    mutationFn: (file: File) => intakeMedicationFromUpload(file),
    onSuccess: (result) => {
      setIntakeResult(result);
      setError(null);
    },
    onError: (mutationError) => {
      setError(mutationError instanceof Error ? mutationError.message : String(mutationError));
    },
  });

  const confirmIntakeMutation = useMutation({
    mutationFn: confirmMedicationIntake,
    onSuccess: async () => {
      setIntakeResult(null);
      setError(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["medication-regimens"] }),
        queryClient.invalidateQueries({ queryKey: ["medication-metrics"] }),
      ]);
    },
  });

  const updateRegimenMutation = useMutation({
    mutationFn: ({ regimenId, active }: { regimenId: string; active: boolean }) =>
      updateMedicationRegimen(regimenId, { active }),
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["medication-regimens"] });
    },
  });

  const deleteRegimenMutation = useMutation({
    mutationFn: deleteMedicationRegimen,
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["medication-regimens"] });
    },
  });

  return {
    regimens: regimensResult?.items ?? [],
    adherenceEvents: metrics?.events ?? [],
    metrics,
    metricsLoading,
    regimensLoading,
    error,
    setError,
    intakeResult,
    setIntakeResult,
    busy:
      intakeTextMutation.isPending ||
      intakeUploadMutation.isPending ||
      confirmIntakeMutation.isPending ||
      regimensLoading ||
      metricsLoading,
    intakeText: (text: string) => intakeTextMutation.mutate(text),
    intakeUpload: (file: File) => intakeUploadMutation.mutate(file),
    confirmIntake: (draftId: string) => confirmIntakeMutation.mutate({ draft_id: draftId }),
    toggleRegimen: (regimenId: string, active: boolean) => updateRegimenMutation.mutate({ regimenId, active }),
    deleteRegimen: deleteRegimenMutation.mutate,
    isPendingIntake: intakeTextMutation.isPending || intakeUploadMutation.isPending,
    isPendingConfirm: confirmIntakeMutation.isPending,
  };
}
