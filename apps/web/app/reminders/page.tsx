"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Calendar, History, ListTodo, X } from "lucide-react";

import { ErrorCard } from "@/components/app/error-card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
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
import { ReminderListItem } from "./components/reminder-list-item";
import { cn } from "@/lib/utils";

export default function RemindersPage() {
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

  const loading = definitionsLoading || upcomingLoading || historyLoading;
  const mutating = createMutation.isPending || patchMutation.isPending;

  return (
    <div className="section-stack relative isolate">
      <div className="dashboard-grounding" />
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Care Coordination</h1>
          <p className="text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl text-sm">
            Manage your clinical schedule, set medication reminders, and review historical adherence outcomes.
          </p>
        </div>
        {!showCreateForm && (
          <Button 
            className="h-11 rounded-xl px-6 font-bold shadow-md gap-2 bg-health-teal hover:bg-health-teal/90"
            onClick={() => setShowCreateForm(true)}
          >
            <Plus className="h-4 w-4" /> Create Reminder
          </Button>
        )}
      </div>

      {showCreateForm && (
        <div className="glass-card border-health-teal/20 shadow-lg animate-in fade-in slide-in-from-top-4">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold tracking-tight">{editingDefinitionId ? "Edit Reminder" : "Create Manual Reminder"}</h2>
            <Button 
              variant="ghost" 
              className="h-8 w-8 rounded-full p-0"
              onClick={() => {
                setShowCreateForm(false);
                setEditingDefinitionId(null);
                resetForm();
              }}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="reminder-title" className="text-[10px] font-bold uppercase tracking-widest opacity-60">Title / Name</Label>
              <Input 
                id="reminder-title"
                placeholder="e.g., Metformin 500mg" 
                value={newReminder.title}
                onChange={(e) => setNewReminder({ ...newReminder, title: e.target.value })}
                className="rounded-lg"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="reminder-type" className="text-[10px] font-bold uppercase tracking-widest opacity-60">Type</Label>
              <Select
                id="reminder-type"
                value={newReminder.reminder_type}
                onChange={(e) => setNewReminder({ ...newReminder, reminder_type: e.target.value as any })}
                className="rounded-lg"
              >
                <option value="medication">Medication</option>
                <option value="mobility">Mobility / Task</option>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="reminder-pattern" className="text-[10px] font-bold uppercase tracking-widest opacity-60">Schedule Type</Label>
              <Select
                id="reminder-pattern"
                value={newReminder.pattern}
                onChange={(e) => setNewReminder({ ...newReminder, pattern: e.target.value as any })}
                className="rounded-lg"
              >
                <option value="daily_fixed_times">Daily (Fixed Time)</option>
                <option value="every_x_hours">Interval (Every X hours)</option>
                <option value="specific_weekdays">Weekly (Specific Days)</option>
                <option value="one_time">One-time</option>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="start-date" className="text-[10px] font-bold uppercase tracking-widest opacity-60">
                {newReminder.pattern === "one_time" ? "Date" : "Start Date"}
              </Label>
              <Input 
                id="start-date"
                type="date"
                value={newReminder.oneTimeDate}
                onChange={(e) => setNewReminder({ ...newReminder, oneTimeDate: e.target.value })}
                className="rounded-lg"
              />
            </div>

            {newReminder.pattern === "every_x_hours" && (
              <div className="space-y-2">
                <Label htmlFor="interval-hours" className="text-[10px] font-bold uppercase tracking-widest opacity-60">Interval (Hours)</Label>
                <Input 
                  id="interval-hours"
                  type="number"
                  min="1"
                  max="24"
                  value={newReminder.interval_hours}
                  onChange={(e) => setNewReminder({ ...newReminder, interval_hours: parseInt(e.target.value) || 1 })}
                  className="rounded-lg"
                />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="reminder-time" className="text-[10px] font-bold uppercase tracking-widest opacity-60">Time</Label>
              <Input 
                id="reminder-time"
                type="time"
                value={newReminder.time}
                onChange={(e) => setNewReminder({ ...newReminder, time: e.target.value })}
                className="rounded-lg"
              />
            </div>

            {newReminder.pattern === "specific_weekdays" && (
              <div className="space-y-3 md:col-span-2">
                <Label className="text-[10px] font-bold uppercase tracking-widest opacity-60">Repeat on</Label>
                <div className="flex flex-wrap gap-2">
                  {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day, idx) => {
                    const dayNum = idx + 1;
                    const isSelected = newReminder.weekdays.includes(dayNum);
                    return (
                      <button
                        key={day}
                        onClick={() => {
                          const next = isSelected 
                            ? newReminder.weekdays.filter(d => d !== dayNum) 
                            : [...newReminder.weekdays, dayNum];
                          setNewReminder({ ...newReminder, weekdays: next.sort() });
                        }}
                        className={cn(
                          "h-10 w-12 rounded-lg border text-xs font-bold transition-all",
                          isSelected 
                            ? "bg-health-teal text-white border-health-teal" 
                            : "border-[color:var(--border-soft)] hover:bg-white/10 dark:hover:bg-black/10"
                        )}
                      >
                        {day}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="reminder-body" className="text-[10px] font-bold uppercase tracking-widest opacity-60">Instructions / Notes (Optional)</Label>
              <Textarea 
                id="reminder-body"
                placeholder="Take with food, avoid caffeine..."
                value={newReminder.body}
                onChange={(e) => setNewReminder({ ...newReminder, body: e.target.value })}
                className="min-h-[80px] rounded-lg"
              />
            </div>
          </div>

          <div className="mt-8 flex items-center justify-end gap-3 border-t border-white/10 pt-6">
            <Button 
              variant="secondary" 
              onClick={() => {
                setShowCreateForm(false);
                setEditingDefinitionId(null);
                resetForm();
              }}
              className="h-11 px-6 rounded-xl"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleCreateReminder}
              disabled={mutating}
              className="h-11 px-8 rounded-xl font-bold shadow-md bg-health-teal hover:bg-health-teal/90"
            >
              {mutating ? (editingDefinitionId ? "Updating..." : "Creating...") : (editingDefinitionId ? "Update Reminder" : "Save Reminder")}
            </Button>
          </div>
        </div>
      )}

      {error && <ErrorCard message={error} />}

      <Tabs defaultValue="today" className="w-full space-y-6 md:space-y-8">
        <div className="flex flex-col gap-4 border-b border-white/10 pb-1 lg:flex-row lg:items-center lg:justify-between">
          <TabsList className="bg-transparent h-auto p-0 gap-4 md:gap-8 overflow-x-auto scrollbar-hide flex-nowrap justify-start">
            <TabsTrigger 
              value="today" 
              className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-health-teal data-[state=active]:bg-transparent data-[state=active]:text-health-teal shadow-none shrink-0"
            >
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                <span>Due Today</span>
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-health-teal-soft text-[10px] text-health-teal font-bold">
                  {todaysOccurrences.length}
                </span>
              </div>
            </TabsTrigger>
            <TabsTrigger 
              value="planned" 
              className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-health-teal data-[state=active]:bg-transparent data-[state=active]:text-health-teal shadow-none shrink-0"
            >
              <div className="flex items-center gap-2">
                <ListTodo className="h-4 w-4" />
                <span>Schedule</span>
              </div>
            </TabsTrigger>
            <TabsTrigger 
              value="history" 
              className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-health-teal data-[state=active]:bg-transparent data-[state=active]:text-health-teal shadow-none shrink-0"
            >
              <div className="flex items-center gap-2">
                <History className="h-4 w-4" />
                <span>History</span>
              </div>
            </TabsTrigger>
          </TabsList>

          <div className="flex items-center gap-2 w-full lg:w-auto pb-2 lg:pb-0">
            <div className="relative w-full lg:w-64">
              <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[color:var(--muted-foreground)] opacity-50" />
              <input 
                type="text" 
                placeholder="Search schedule..."
                aria-label="Search schedule"
                className="h-9 w-full rounded-lg border border-white/10 bg-white/5 pl-9 pr-4 text-xs focus:border-health-teal focus:outline-none"
              />
            </div>
          </div>
        </div>

        <TabsContent value="today" className="mt-0 space-y-6">
          <div className="grid gap-3">
            {todaysOccurrences.length > 0 ? (
              todaysOccurrences.map((occurrence) => (
                <ReminderListItem 
                  key={occurrence.id} 
                  occurrence={occurrence} 
                  definition={definitionMap.get(occurrence.reminder_definition_id)}
                  onAction={(action, snoozeMinutes) => actionMutation.mutate({ occurrenceId: occurrence.id, action, snoozeMinutes })}
                  actionDisabled={actionMutation.isPending || loading}
                  onEdit={() => {
                    const definition = definitionMap.get(occurrence.reminder_definition_id);
                    if (definition) startEditDefinition(definition);
                  }}
                />
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-center space-y-3 glass-card">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-health-teal-soft text-health-teal/40">
                  <Calendar className="h-6 w-6" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-bold tracking-tight">Nothing due today</p>
                  <p className="text-xs text-[color:var(--muted-foreground)] opacity-60">You&apos;re all caught up on your clinical schedule.</p>
                </div>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="planned" className="mt-0 space-y-6">
          <div className="grid gap-3">
            {definitions.length > 0 ? (
              definitions.map((definition) => (
                <ReminderListItem 
                  key={definition.id} 
                  definition={definition} 
                  onToggle={() => toggleMutation.mutate({ id: definition.id, active: !definition.active })}
                  toggleDisabled={toggleMutation.isPending || loading}
                  onEdit={() => startEditDefinition(definition)}
                />
              ))
            ) : (
              <div className="text-center py-20 text-[color:var(--muted-foreground)] glass-card">No planned reminders.</div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="history" className="mt-0 space-y-6">
          <div className="grid gap-3">
            {history.length > 0 ? (
              history.map((occurrence) => (
                <ReminderListItem 
                  key={occurrence.id} 
                  occurrence={occurrence} 
                  definition={definitionMap.get(occurrence.reminder_definition_id)}
                  onAction={(action, snoozeMinutes) => actionMutation.mutate({ occurrenceId: occurrence.id, action, snoozeMinutes })}
                  actionDisabled={actionMutation.isPending || loading}
                  onEdit={() => {
                    const definition = definitionMap.get(occurrence.reminder_definition_id);
                    if (definition) startEditDefinition(definition);
                  }}
                />
              ))
            ) : (
              <div className="text-center py-20 text-[color:var(--muted-foreground)] glass-card">No historical records found.</div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
