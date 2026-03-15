"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus, Search, Calendar, History, ListTodo, X } from "lucide-react";

import { ErrorCard } from "@/components/app/error-card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
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
  ReminderOccurrenceApi,
} from "@/lib/types";
import { ReminderListItem } from "./components/reminder-list-item";
import { cn } from "@/lib/utils";

export default function RemindersPage() {
  const [definitions, setDefinitions] = useState<ReminderDefinitionApi[]>([]);
  const [upcoming, setUpcoming] = useState<ReminderOccurrenceApi[]>([]);
  const [history, setHistory] = useState<ReminderOccurrenceApi[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [toggleLoadingId, setToggleLoadingId] = useState<string | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
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

  const definitionMap = useMemo(() => new Map(definitions.map((item) => [item.id, item])), [definitions]);
  const todayKey = new Date().toDateString();
  const todaysOccurrences = useMemo(
    () => upcoming.filter((occurrence) => new Date(occurrence.trigger_at).toDateString() === todayKey),
    [todayKey, upcoming],
  );

  async function loadStructuredData() {
    setLoading(true);
    try {
      const [definitionData, upcomingData, historyData] = await Promise.all([
        listReminderDefinitions(),
        listUpcomingReminderOccurrences(),
        listReminderHistory(),
      ]);
      setDefinitions(definitionData.items);
      setUpcoming(upcomingData.items);
      setHistory(historyData.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadStructuredData();
  }, []);

  async function toggleDefinition(definition: ReminderDefinitionApi) {
    setError(null);
    setToggleLoadingId(definition.id);
    try {
      await patchReminderDefinition(definition.id, { active: !definition.active });
      await loadStructuredData();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setToggleLoadingId(null);
    }
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

  async function handleOccurrenceAction(
    occurrenceId: string,
    action: "taken" | "skipped" | "snooze",
    snoozeMinutes?: number,
  ) {
    setError(null);
    setActionLoadingId(occurrenceId);
    try {
      await actOnReminderOccurrence({
        occurrenceId,
        action,
        snooze_minutes: snoozeMinutes,
      });
      await loadStructuredData();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleCreateReminder() {
    if (!newReminder.title.trim()) {
      setError("Title is required");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const schedule: any = {
        pattern: newReminder.pattern,
        timezone,
        offset_minutes: 0,
        as_needed: false,
        metadata: {},
      };

      if (newReminder.pattern === "one_time") {
        schedule.start_date = newReminder.oneTimeDate;
        schedule.times = [newReminder.time];
      } else if (newReminder.pattern === "daily_fixed_times") {
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
        await patchReminderDefinition(editingDefinitionId, {
          title: newReminder.title,
          body: newReminder.body,
          schedule,
        });
      } else {
        await createReminderDefinition({
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

      setShowCreateForm(false);
      setEditingDefinitionId(null);
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
      await loadStructuredData();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="section-stack">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Care Coordination</h1>
          <p className="text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl text-sm">
            Manage your clinical schedule, set medication reminders, and review historical adherence outcomes.
          </p>
        </div>
        {!showCreateForm && (
          <Button 
            className="h-11 rounded-xl px-6 font-bold shadow-sm gap-2"
            onClick={() => setShowCreateForm(true)}
          >
            <Plus className="h-4 w-4" /> Create Reminder
          </Button>
        )}
      </div>

      {showCreateForm && (
        <Card className="border-[color:var(--accent)]/20 shadow-lg animate-in fade-in slide-in-from-top-4">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold tracking-tight">{editingDefinitionId ? "Edit Reminder" : "Create Manual Reminder"}</h2>
              <Button 
                variant="ghost" 
                className="h-8 w-8 rounded-full p-0"
                onClick={() => {
                  setShowCreateForm(false);
                  setEditingDefinitionId(null);
                }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="reminder-title">Title / Name</Label>
                <Input 
                  id="reminder-title"
                  placeholder="e.g., Metformin 500mg" 
                  value={newReminder.title}
                  onChange={(e) => setNewReminder({ ...newReminder, title: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="reminder-type">Type</Label>
                <Select
                  id="reminder-type"
                  value={newReminder.reminder_type}
                  onChange={(e) => setNewReminder({ ...newReminder, reminder_type: e.target.value as any })}
                >
                  <option value="medication">Medication</option>
                  <option value="mobility">Mobility / Task</option>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="reminder-pattern">Schedule Type</Label>
                <Select
                  id="reminder-pattern"
                  value={newReminder.pattern}
                  onChange={(e) => setNewReminder({ ...newReminder, pattern: e.target.value as any })}
                >
                  <option value="daily_fixed_times">Daily (Fixed Time)</option>
                  <option value="every_x_hours">Interval (Every X hours)</option>
                  <option value="specific_weekdays">Weekly (Specific Days)</option>
                  <option value="one_time">One-time</option>
                </Select>
              </div>

              {newReminder.pattern === "one_time" && (
                <div className="space-y-2">
                  <Label htmlFor="one-time-date">Date</Label>
                  <Input 
                    id="one-time-date"
                    type="date"
                    value={newReminder.oneTimeDate}
                    onChange={(e) => setNewReminder({ ...newReminder, oneTimeDate: e.target.value })}
                  />
                </div>
              )}
              
              {newReminder.pattern !== "one_time" && (
                <div className="space-y-2">
                  <Label htmlFor="start-date">Start date</Label>
                  <Input 
                    id="start-date"
                    type="date"
                    value={newReminder.oneTimeDate}
                    onChange={(e) => setNewReminder({ ...newReminder, oneTimeDate: e.target.value })}
                  />
                </div>
              )}

              {newReminder.pattern === "every_x_hours" && (
                <div className="space-y-2">
                  <Label htmlFor="interval-hours">Interval (Hours)</Label>
                  <Input 
                    id="interval-hours"
                    type="number"
                    min="1"
                    max="24"
                    value={newReminder.interval_hours}
                    onChange={(e) => setNewReminder({ ...newReminder, interval_hours: parseInt(e.target.value) || 1 })}
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="reminder-time">Time</Label>
                <Input 
                  id="reminder-time"
                  type="time"
                  value={newReminder.time}
                  onChange={(e) => setNewReminder({ ...newReminder, time: e.target.value })}
                />
              </div>

              {newReminder.pattern === "specific_weekdays" && (
                <div className="space-y-3 md:col-span-2">
                  <Label>Repeat on</Label>
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
                              ? "bg-[color:var(--accent)] text-white border-[color:var(--accent)]" 
                              : "border-[color:var(--border-soft)] hover:bg-[color:var(--panel-soft)]"
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
                <Label htmlFor="reminder-body">Instructions / Notes (Optional)</Label>
                <Textarea 
                  id="reminder-body"
                  placeholder="Take with food, avoid caffeine..."
                  value={newReminder.body}
                  onChange={(e) => setNewReminder({ ...newReminder, body: e.target.value })}
                  className="min-h-[80px]"
                />
              </div>
            </div>

            <div className="mt-8 flex items-center justify-end gap-3 border-t border-[color:var(--border-soft)] pt-6">
              <Button 
                variant="secondary" 
                onClick={() => {
                  setShowCreateForm(false);
                  setEditingDefinitionId(null);
                }}
                className="h-11 px-6 rounded-xl"
              >
                Cancel
              </Button>
              <Button 
                onClick={handleCreateReminder}
                disabled={loading}
                className="h-11 px-8 rounded-xl font-bold shadow-md bg-[color:var(--accent)] hover:bg-[color:var(--accent)]/90"
              >
                {loading ? (editingDefinitionId ? "Updating..." : "Creating...") : (editingDefinitionId ? "Update Reminder" : "Save Reminder")}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {error && <ErrorCard message={error} />}

      <Tabs defaultValue="today" className="w-full space-y-6 md:space-y-8">
        <div className="flex flex-col gap-4 border-b border-[color:var(--border-soft)] pb-1 lg:flex-row lg:items-center lg:justify-between">
          <TabsList className="bg-transparent h-auto p-0 gap-4 md:gap-8 overflow-x-auto scrollbar-hide flex-nowrap justify-start">
            <TabsTrigger 
              value="today" 
              className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-[color:var(--accent)] data-[state=active]:bg-transparent data-[state=active]:text-[color:var(--foreground)] shadow-none shrink-0"
            >
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                <span>Due Today</span>
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[color:var(--accent)]/10 text-[10px] text-[color:var(--accent)]">
                  {todaysOccurrences.length}
                </span>
              </div>
            </TabsTrigger>
            <TabsTrigger 
              value="planned" 
              className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-[color:var(--accent)] data-[state=active]:bg-transparent data-[state=active]:text-[color:var(--foreground)] shadow-none shrink-0"
            >
              <div className="flex items-center gap-2">
                <ListTodo className="h-4 w-4" />
                <span>Schedule</span>
              </div>
            </TabsTrigger>
            <TabsTrigger 
              value="history" 
              className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-[color:var(--accent)] data-[state=active]:bg-transparent data-[state=active]:text-[color:var(--foreground)] shadow-none shrink-0"
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
                className="h-9 w-full rounded-lg border border-[color:var(--border-soft)] bg-[color:var(--surface)] pl-9 pr-4 text-xs focus:border-[color:var(--accent)] focus:outline-none"
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
                  onAction={(action, snoozeMinutes) => handleOccurrenceAction(occurrence.id, action, snoozeMinutes)}
                  actionDisabled={actionLoadingId === occurrence.id || loading}
                />
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-center space-y-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[color:var(--accent)]/5 text-[color:var(--accent)]/40">
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
                  onToggle={() => toggleDefinition(definition)}
                  toggleDisabled={toggleLoadingId === definition.id || loading}
                  onEdit={() => startEditDefinition(definition)}
                />
              ))
            ) : (
              <div className="text-center py-20 text-[color:var(--muted-foreground)]">No planned reminders.</div>
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
                  onAction={(action, snoozeMinutes) => handleOccurrenceAction(occurrence.id, action, snoozeMinutes)}
                  actionDisabled={actionLoadingId === occurrence.id || loading}
                />
              ))
            ) : (
              <div className="text-center py-20 text-[color:var(--muted-foreground)]">No historical records found.</div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
