"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus, Search, Calendar, History, ListTodo } from "lucide-react";

import { ErrorCard } from "@/components/app/error-card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
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

  return (
    <div className="section-stack">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Care Coordination</h1>
          <p className="text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl text-sm">
            Manage your clinical schedule, set medication reminders, and review historical adherence outcomes.
          </p>
        </div>
        <Button className="h-11 rounded-xl px-6 font-bold shadow-sm gap-2">
          <Plus className="h-4 w-4" /> Create Reminder
        </Button>
      </div>

      {error && <ErrorCard message={error} />}

      <Tabs defaultValue="today" className="w-full space-y-8">
        <div className="flex flex-col gap-4 border-b border-[color:var(--border-soft)] pb-1 sm:flex-row sm:items-center sm:justify-between">
          <TabsList className="bg-transparent h-auto p-0 gap-8">
            <TabsTrigger 
              value="today" 
              className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-[color:var(--accent)] data-[state=active]:bg-transparent data-[state=active]:text-[color:var(--foreground)] shadow-none"
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
              className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-[color:var(--accent)] data-[state=active]:bg-transparent data-[state=active]:text-[color:var(--foreground)] shadow-none"
            >
              <div className="flex items-center gap-2">
                <ListTodo className="h-4 w-4" />
                <span>Schedule</span>
              </div>
            </TabsTrigger>
            <TabsTrigger 
              value="history" 
              className="relative h-10 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-sm font-semibold text-[color:var(--muted-foreground)] transition-all data-[state=active]:border-[color:var(--accent)] data-[state=active]:bg-transparent data-[state=active]:text-[color:var(--foreground)] shadow-none"
            >
              <div className="flex items-center gap-2">
                <History className="h-4 w-4" />
                <span>History</span>
              </div>
            </TabsTrigger>
          </TabsList>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[color:var(--muted-foreground)] opacity-50" />
              <input 
                type="text" 
                placeholder="Search schedule..."
                aria-label="Search schedule"
                className="h-9 w-64 rounded-lg border border-[color:var(--border-soft)] bg-[color:var(--surface)] pl-9 pr-4 text-xs focus:border-[color:var(--accent)] focus:outline-none"
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
                />
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-center space-y-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[color:var(--accent)]/5 text-[color:var(--accent)]/40">
                  <Calendar className="h-6 w-6" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-bold tracking-tight">Nothing due today</p>
                  <p className="text-xs text-[color:var(--muted-foreground)] opacity-60">You're all caught up on your clinical schedule.</p>
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
