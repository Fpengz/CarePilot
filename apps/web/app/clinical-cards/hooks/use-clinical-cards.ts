"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { generateClinicalCard, getClinicalCard, listClinicalCards } from "@/lib/api/meal-client";
import type { ClinicalCardApi } from "@/lib/types";

function dateString(value: Date): string {
  return value.toISOString().slice(0, 10);
}

export function useClinicalCards() {
  const queryClient = useQueryClient();
  const defaultEnd = dateString(new Date());
  const defaultStart = dateString(new Date(Date.now() - 6 * 24 * 60 * 60 * 1000));
  
  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(defaultEnd);
  const [format, setFormat] = useState<"sectioned" | "soap">("sectioned");
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: listData, isLoading: listLoading } = useQuery({
    queryKey: ["clinical-cards"],
    queryFn: () => listClinicalCards(20),
  });

  const cards = listData?.items ?? [];

  const { data: selectedData, isLoading: cardLoading } = useQuery({
    queryKey: ["clinical-card", selectedCardId],
    queryFn: () => selectedCardId ? getClinicalCard(selectedCardId) : Promise.resolve(null),
    enabled: !!selectedCardId,
  });

  const selectedCard = selectedData?.card ?? cards[0] ?? null;

  const generateMutation = useMutation({
    mutationFn: generateClinicalCard,
    onSuccess: (response) => {
      setSelectedCardId(response.card.id);
      queryClient.invalidateQueries({ queryKey: ["clinical-cards"] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  return {
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    format,
    setFormat,
    cards,
    selectedCard,
    selectedCardId,
    setSelectedCardId,
    error,
    setError,
    loading: listLoading || cardLoading || generateMutation.isPending,
    isGenerating: generateMutation.isPending,
    generateCard: () => generateMutation.mutate({
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      format,
    }),
    refresh: () => queryClient.invalidateQueries({ queryKey: ["clinical-cards"] }),
  };
}
