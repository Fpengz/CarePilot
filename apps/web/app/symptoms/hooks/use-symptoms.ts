"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createSymptomCheckIn, getSymptomSummary, listSymptomCheckIns } from "@/lib/api/meal-client";

export function useSymptoms() {
  const queryClient = useQueryClient();
  const [severity, setSeverity] = useState(3);
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [freeText, setFreeText] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: checkinsData, isLoading: checkinsLoading } = useQuery({
    queryKey: ["symptom-checkins"],
    queryFn: () => listSymptomCheckIns({ limit: 20 }),
  });

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["symptom-summary"],
    queryFn: () => getSymptomSummary(),
  });

  const submitMutation = useMutation({
    mutationFn: createSymptomCheckIn,
    onSuccess: () => {
      setFreeText("");
      setSelectedSymptoms([]);
      setSeverity(3);
      queryClient.invalidateQueries({ queryKey: ["symptom-checkins"] });
      queryClient.invalidateQueries({ queryKey: ["symptom-summary"] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const toggleSymptom = (symptom: string) => {
    setSelectedSymptoms(prev => 
      prev.includes(symptom) ? prev.filter(s => s !== symptom) : [...prev, symptom]
    );
  };

  return {
    severity,
    setSeverity,
    selectedSymptoms,
    toggleSymptom,
    freeText,
    setFreeText,
    error,
    setError,
    checkIns: checkinsData?.items ?? [],
    summary,
    loading: checkinsLoading || summaryLoading,
    submitting: submitMutation.isPending,
    logCheckIn: () => submitMutation.mutate({ 
      severity, 
      symptom_codes: selectedSymptoms.map(s => s.toLowerCase()), 
      free_text: freeText.trim() || undefined, 
      context: {} 
    }),
    refresh: () => queryClient.invalidateQueries(),
  };
}
