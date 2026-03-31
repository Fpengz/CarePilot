"use client";

import { Plus, Search, Calendar, History, ListTodo, X } from "lucide-react";

import { ErrorCard } from "@/components/app/error-card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ReminderListItem } from "./components/reminder-list-item";
import { cn } from "@/lib/utils";
import { useReminders } from "./hooks/use-reminders";

export default function RemindersPage() {
  const {
    definitions,
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
    loading,
    mutating,
    toggleReminder,
    actOnOccurrence,
    handleCreateReminder,
    startEditDefinition,
    resetForm,
    isActionPending,
    isTogglePending,
  } = useReminders();

  return (
    <main className="section-stack relative isolate max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pb-12 bg-background min-h-screen">
      <div className="dashboard-grounding" aria-hidden="true" />
      
      <header className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between py-10">
        <div className="space-y-1">
          <h1 className="text-h1 font-display tracking-tight text-foreground">Care Coordination</h1>
          <p className="text-muted-foreground leading-relaxed max-w-2xl text-sm font-medium">
            Manage your clinical schedule, set medication reminders, and review historical adherence outcomes.
          </p>
        </div>
        {!showCreateForm && (
          <Button 
            className="h-11 rounded-xl px-6 font-bold shadow-sm gap-2"
            onClick={() => setShowCreateForm(true)}
          >
            <Plus className="h-4 w-4" aria-hidden="true" /> Create Reminder
          </Button>
        )}
      </header>

      {showCreateForm && (
        <section 
          className="bg-panel border border-border-soft rounded-2xl p-8 shadow-sm animate-in fade-in slide-in-from-top-4 mb-12"
          aria-labelledby="form-heading"
        >
          <div className="flex items-center justify-between mb-8">
            <h2 id="form-heading" className="text-xl font-semibold tracking-tight text-foreground">
              {editingDefinitionId ? "Edit Clinical Reminder" : "Create Manual Reminder"}
            </h2>
            <Button 
              variant="ghost" 
              className="h-9 w-9 rounded-full p-0"
              onClick={() => {
                setShowCreateForm(false);
                setEditingDefinitionId(null);
                resetForm();
              }}
              aria-label="Close form"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="grid gap-8 md:grid-cols-2">
            <div className="space-y-2.5">
              <Label htmlFor="reminder-title" className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">Title / Name</Label>
              <Input 
                id="reminder-title"
                placeholder="e.g., Metformin 500mg" 
                value={newReminder.title}
                onChange={(e) => setNewReminder({ ...newReminder, title: e.target.value })}
                className="rounded-xl border-border-soft"
              />
            </div>

            <div className="space-y-2.5">
              <Label htmlFor="reminder-type" className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">Type</Label>
              <Select
                id="reminder-type"
                value={newReminder.reminder_type}
                onChange={(e) => setNewReminder({ ...newReminder, reminder_type: e.target.value as any })}
                className="rounded-xl border-border-soft"
              >
                <option value="medication">Medication</option>
                <option value="mobility">Mobility / Task</option>
              </Select>
            </div>

            <div className="space-y-2.5">
              <Label htmlFor="reminder-pattern" className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">Schedule Type</Label>
              <Select
                id="reminder-pattern"
                value={newReminder.pattern}
                onChange={(e) => setNewReminder({ ...newReminder, pattern: e.target.value as any })}
                className="rounded-xl border-border-soft"
              >
                <option value="daily_fixed_times">Daily (Fixed Time)</option>
                <option value="every_x_hours">Interval (Every X hours)</option>
                <option value="specific_weekdays">Weekly (Specific Days)</option>
                <option value="one_time">One-time</option>
              </Select>
            </div>

            <div className="space-y-2.5">
              <Label htmlFor="start-date" className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">
                {newReminder.pattern === "one_time" ? "Date" : "Start Date"}
              </Label>
              <Input 
                id="start-date"
                type="date"
                value={newReminder.oneTimeDate}
                onChange={(e) => setNewReminder({ ...newReminder, oneTimeDate: e.target.value })}
                className="rounded-xl border-border-soft"
              />
            </div>

            {newReminder.pattern === "every_x_hours" && (
              <div className="space-y-2.5">
                <Label htmlFor="interval-hours" className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">Interval (Hours)</Label>
                <Input 
                  id="interval-hours"
                  type="number"
                  min="1"
                  max="24"
                  value={newReminder.interval_hours}
                  onChange={(e) => setNewReminder({ ...newReminder, interval_hours: parseInt(e.target.value) || 1 })}
                  className="rounded-xl border-border-soft"
                />
              </div>
            )}

            <div className="space-y-2.5">
              <Label htmlFor="reminder-time" className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">Time</Label>
              <Input 
                id="reminder-time"
                type="time"
                value={newReminder.time}
                onChange={(e) => setNewReminder({ ...newReminder, time: e.target.value })}
                className="rounded-xl border-border-soft"
              />
            </div>

            {newReminder.pattern === "specific_weekdays" && (
              <div className="space-y-4 md:col-span-2">
                <Label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">Repeat on</Label>
                <div className="flex flex-wrap gap-3">
                  {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day, idx) => {
                    const dayNum = idx + 1;
                    const isSelected = newReminder.weekdays.includes(dayNum);
                    return (
                      <button
                        key={day}
                        type="button"
                        onClick={() => {
                          const next = isSelected 
                            ? newReminder.weekdays.filter(d => d !== dayNum) 
                            : [...newReminder.weekdays, dayNum];
                          setNewReminder({ ...newReminder, weekdays: next.sort() });
                        }}
                        className={cn(
                          "h-11 w-14 rounded-xl border text-[11px] font-bold transition-all uppercase tracking-widest",
                          isSelected 
                            ? "bg-accent-teal text-white border-accent-teal shadow-sm" 
                            : "border-border-soft bg-surface hover:bg-panel text-muted-foreground"
                        )}
                      >
                        {day}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="space-y-2.5 md:col-span-2">
              <Label htmlFor="reminder-body" className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">Instructions / Notes (Optional)</Label>
              <Textarea 
                id="reminder-body"
                placeholder="e.g., Take with food, avoid caffeine..."
                value={newReminder.body}
                onChange={(e) => setNewReminder({ ...newReminder, body: e.target.value })}
                className="min-h-[100px] rounded-xl border-border-soft resize-none leading-relaxed"
              />
            </div>
          </div>

          <div className="mt-10 flex items-center justify-end gap-4 border-t border-border-soft pt-8">
            <Button 
              variant="secondary" 
              onClick={() => {
                setShowCreateForm(false);
                setEditingDefinitionId(null);
                resetForm();
              }}
              className="h-12 px-8 rounded-xl font-semibold"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleCreateReminder}
              disabled={mutating}
              className="h-12 px-10 rounded-xl font-bold shadow-sm"
            >
              {mutating ? (editingDefinitionId ? "Updating..." : "Creating...") : (editingDefinitionId ? "Update Reminder" : "Save Reminder")}
            </Button>
          </div>
        </section>
      )}

      {error && (
        <div className="mb-8" role="alert">
          <ErrorCard message={error} />
        </div>
      )}

      <Tabs defaultValue="today" className="w-full space-y-10">
        <div className="flex flex-col gap-6 border-b border-border-soft pb-1 lg:flex-row lg:items-center lg:justify-between">
          <TabsList className="bg-transparent h-auto p-0 gap-6 md:gap-10 overflow-x-auto scrollbar-hide flex-nowrap justify-start">
            <TabsTrigger 
              value="today" 
              className="relative h-11 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-[13px] font-bold uppercase tracking-widest text-muted-foreground transition-all data-[state=active]:border-accent-teal data-[state=active]:bg-transparent data-[state=active]:text-foreground shadow-none shrink-0"
            >
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4" aria-hidden="true" />
                <span>Due Today</span>
                <span className="flex h-5 min-w-5 px-1 items-center justify-center rounded-lg bg-accent-teal/10 text-[10px] text-accent-teal font-bold">
                  {todaysOccurrences.length}
                </span>
              </div>
            </TabsTrigger>
            <TabsTrigger 
              value="planned" 
              className="relative h-11 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-[13px] font-bold uppercase tracking-widest text-muted-foreground transition-all data-[state=active]:border-accent-teal data-[state=active]:bg-transparent data-[state=active]:text-foreground shadow-none shrink-0"
            >
              <div className="flex items-center gap-3">
                <ListTodo className="h-4 w-4" aria-hidden="true" />
                <span>Schedule</span>
              </div>
            </TabsTrigger>
            <TabsTrigger 
              value="history" 
              className="relative h-11 rounded-none border-b-2 border-transparent bg-transparent px-1 pb-4 pt-0 text-[13px] font-bold uppercase tracking-widest text-muted-foreground transition-all data-[state=active]:border-accent-teal data-[state=active]:bg-transparent data-[state=active]:text-foreground shadow-none shrink-0"
            >
              <div className="flex items-center gap-3">
                <History className="h-4 w-4" aria-hidden="true" />
                <span>History</span>
              </div>
            </TabsTrigger>
          </TabsList>

          <div className="flex items-center gap-3 w-full lg:w-auto pb-2 lg:pb-0">
            <div className="relative w-full lg:w-72">
              <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground opacity-50" aria-hidden="true" />
              <input 
                type="text" 
                placeholder="Search clinical schedule..."
                aria-label="Search schedule"
                className="h-10 w-full rounded-xl border border-border-soft bg-panel pl-10 pr-4 text-[13px] font-medium focus:bg-surface focus:border-accent-teal/40 focus:outline-none transition-colors"
              />
            </div>
          </div>
        </div>

        <TabsContent value="today" className="mt-0 outline-none">
          <section className="grid gap-4" aria-label="Reminders due today">
            {todaysOccurrences.length > 0 ? (
              todaysOccurrences.map((occurrence) => (
                <ReminderListItem 
                  key={occurrence.id} 
                  occurrence={occurrence} 
                  definition={definitionMap.get(occurrence.reminder_definition_id)}
                  onAction={(action, snoozeMinutes) => actOnOccurrence({ occurrenceId: occurrence.id, action, snoozeMinutes })}
                  actionDisabled={isActionPending || loading}
                  onEdit={() => {
                    const definition = definitionMap.get(occurrence.reminder_definition_id);
                    if (definition) startEditDefinition(definition);
                  }}
                />
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-24 text-center space-y-4 bg-panel border border-dashed border-border-soft rounded-3xl">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent-teal/5 text-accent-teal/40">
                  <Calendar className="h-7 w-7" aria-hidden="true" />
                </div>
                <div className="space-y-1.5">
                  <p className="text-base font-bold tracking-tight text-foreground">Nothing due today</p>
                  <p className="text-[13px] text-muted-foreground font-medium max-w-xs leading-relaxed">You&apos;re all caught up on your clinical schedule.</p>
                </div>
              </div>
            )}
          </section>
        </TabsContent>

        <TabsContent value="planned" className="mt-0 outline-none">
          <section className="grid gap-4" aria-label="Planned reminders">
            {definitions.length > 0 ? (
              definitions.map((definition) => (
                <ReminderListItem 
                  key={definition.id} 
                  definition={definition} 
                  onToggle={() => toggleReminder(definition.id, !definition.active)}
                  toggleDisabled={isTogglePending || loading}
                  onEdit={() => startEditDefinition(definition)}
                />
              ))
            ) : (
              <div className="text-center py-24 bg-panel border border-dashed border-border-soft rounded-3xl text-muted-foreground text-[13px] font-medium italic opacity-60">
                No planned reminders observed.
              </div>
            )}
          </section>
        </TabsContent>

        <TabsContent value="history" className="mt-0 outline-none">
          <section className="grid gap-4" aria-label="Reminder history">
            {history.length > 0 ? (
              history.map((occurrence) => (
                <ReminderListItem 
                  key={occurrence.id} 
                  occurrence={occurrence} 
                  definition={definitionMap.get(occurrence.reminder_definition_id)}
                  onAction={(action, snoozeMinutes) => actOnOccurrence({ occurrenceId: occurrence.id, action, snoozeMinutes })}
                  actionDisabled={isActionPending || loading}
                  onEdit={() => {
                    const definition = definitionMap.get(occurrence.reminder_definition_id);
                    if (definition) startEditDefinition(definition);
                  }}
                />
              ))
            ) : (
              <div className="text-center py-24 bg-panel border border-dashed border-border-soft rounded-3xl text-muted-foreground text-[13px] font-medium italic opacity-60">
                No historical adherence records found.
              </div>
            )}
          </section>
        </TabsContent>
      </Tabs>
    </main>
  );
}
