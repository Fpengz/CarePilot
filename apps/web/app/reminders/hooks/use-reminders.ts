"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  actOnReminderOccurrence,
  createReminderDefinition,
  listReminderDefinitions,
  listReminderHistory,
  listUpcomingReminderOccurrences,
  patchReminderDefinition,
} from "@/lib/api/reminder-client";
import type {
  ReminderDefinitionApi,
} from "@/lib/types";
import { APP_TIMEZONE, formatDate } from "@/lib/time";

export function useReminders() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingDefinitionId, setEditingDefinitionId] = useState<string | null>(null);
  const [newReminder, setNewReminder] = useState({
    title: "",
    body: "",
    reminder_type: "medication" as "medication" | "mobility",
    pattern: "daily_fixed_times" as any,
    time: "08:00",
    interval_hours: 4,
    weekdays: [] as number[],
    oneTimeDate: new Date().toISOString().split("T")[0],
  });

  // Queries
  const { data: definitionsData, isLoading: definitionsLoading } = useQuery({
    queryKey: ["reminder-definitions"],
    queryFn: listReminderDefinitions,
  });
  const { data: upcomingData, isLoading: upcomingLoading } = useQuery({
    queryKey: ["reminder-upcoming"],
    queryFn: listUpcomingReminderOccurrences,
  });
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ["reminder-history"],
    queryFn: listReminderHistory,
  });

  const definitions = definitionsData?.items ?? [];
  const upcoming = upcomingData?.items ?? [];
  const history = historyData?.items ?? [];

  const definitionMap = useMemo(() => new Map(definitions.map((item) => [item.id, item])), [definitions]);
  const todayKey = useMemo(() => formatDate(new Date()), []);
  const todaysOccurrences = useMemo(
    () => upcoming.filter((occurrence) => formatDate(occurrence.trigger_at) === todayKey),
    [todayKey, upcoming],
  );

  // Mutations
  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => 
      patchReminderDefinition(id, { active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reminder-definitions"] });
      queryClient.invalidateQueries({ queryKey: ["reminder-upcoming"] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const actionMutation = useMutation({
    mutationFn: (params: { occurrenceId: string; action: "taken" | "skipped" | "snooze"; snoozeMinutes?: number }) =>
      actOnReminderOccurrence(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reminder-upcoming"] });
      queryClient.invalidateQueries({ queryKey: ["reminder-history"] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const createMutation = useMutation({
    mutationFn: createReminderDefinition,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reminder-definitions"] });
      queryClient.invalidateQueries({ queryKey: ["reminder-upcoming"] });
      setShowCreateForm(false);
      resetForm();
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const patchMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: any }) => 
      patchReminderDefinition(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reminder-definitions"] });
      queryClient.invalidateQueries({ queryKey: ["reminder-upcoming"] });
      setShowCreateForm(false);
      setEditingDefinitionId(null);
      resetForm();
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  function resetForm() {
    setNewReminder({
      title: "",
      body: "",
      reminder_type: "medication",
      pattern: "daily_fixed_times",
      time: "08:00",
      interval_hours: 4,
      weekdays: [],
      oneTimeDate: new Date().toISOString().split("T")[0],
    });
  }

  function startEditDefinition(definition: ReminderDefinitionApi) {
    const schedule = definition.schedule;
    const time = schedule.times?.[0] ?? "08:00";
    const oneTimeDate = schedule.start_date ? schedule.start_date.split("T")[0] : new Date().toISOString().split("T")[0];
    setEditingDefinitionId(definition.id);
    setNewReminder({
      title: definition.title,
      body: definition.body ?? "",
      reminder_type: definition.reminder_type,
      pattern: schedule.pattern as any,
      time,
      interval_hours: schedule.interval_hours ?? 4,
      weekdays: schedule.weekdays ?? [],
      oneTimeDate,
    });
    setShowCreateForm(true);
  }

  async function handleCreateReminder() {
    if (!newReminder.title.trim()) {
      setError("Title is required");
      return;
    }

    const timezone = APP_TIMEZONE;
    const schedule: any = {
      pattern: newReminder.pattern,
      timezone,
      offset_minutes: 0,
      as_needed: false,
      metadata: {},
    };

    if (newReminder.pattern === "one_time" || newReminder.pattern === "daily_fixed_times") {
      schedule.start_date = newReminder.oneTimeDate;
      schedule.times = [newReminder.time];
    } else if (newReminder.pattern === "every_x_hours") {
      schedule.start_date = newReminder.oneTimeDate;
      schedule.interval_hours = newReminder.interval_hours;
      schedule.times = [newReminder.time];
    } else if (newReminder.pattern === "specific_weekdays") {
      schedule.start_date = newReminder.oneTimeDate;
      schedule.weekdays = newReminder.weekdays;
      schedule.times = [newReminder.time];
    }

    if (editingDefinitionId) {
      patchMutation.mutate({
        id: editingDefinitionId,
        payload: {
          title: newReminder.title,
          body: newReminder.body,
          schedule,
        },
      });
    } else {
      createMutation.mutate({
        title: newReminder.title,
        body: newReminder.body,
        reminder_type: newReminder.reminder_type,
        medication_name: newReminder.reminder_type === "medication" ? newReminder.title : undefined,
        dosage_text: newReminder.reminder_type === "medication" ? "as prescribed" : "",
        schedule,
        active: true,
        source: "manual",
      });
    }
  }

  return {
    definitions,
    upcoming,
    history,
    definitionMap,
    todaysOccurrences,
    error,
    setError,
    showCreateForm,
    setShowCreateForm,
    editingDefinitionId,
    setEditingDefinitionId,
    newReminder,
    setNewReminder,
    loading: definitionsLoading || upcomingLoading || historyLoading,
    mutating: createMutation.isPending || patchMutation.isPending,
    toggleReminder: (id: string, active: boolean) => toggleMutation.mutate({ id, active }),
    actOnOccurrence: actionMutation.mutate,
    handleCreateReminder,
    startEditDefinition,
    resetForm,
    isActionPending: actionMutation.isPending,
    isTogglePending: toggleMutation.isPending,
  };
}
